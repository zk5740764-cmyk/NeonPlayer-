// Add these pieces into StreamX. Package names assumed — adjust to match
// your actual module structure (data/remote, data/local, data/repository).

// ─────────────────────────────────────────────────────────────
// 1. Retrofit API
// ─────────────────────────────────────────────────────────────
package com.streamx.data.remote

import retrofit2.http.GET

data class RemoteVideoDto(
    val id: String,
    val title: String,
    val channel: String,
    val thumbnail: String,
    val duration: Int,
    val category: String
)

interface JsDelivrApi {
    // Pin to a tag/commit in production instead of @main so an app in the
    // wild never gets a schema change mid-flight without an update.
    @GET("gh/USERNAME/REPO@main/videos.json")
    suspend fun getVideos(): List<RemoteVideoDto>
}

// ─────────────────────────────────────────────────────────────
// 2. Room entity + DAO
// ─────────────────────────────────────────────────────────────
package com.streamx.data.local

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Insert
import androidx.room.OnConflictStrategy

@Entity(tableName = "remote_videos")
data class RemoteVideoEntity(
    @PrimaryKey val id: String,
    val title: String,
    val channel: String,
    val thumbnail: String,
    val duration: Int,
    val category: String,
    val fetchedAt: Long
)

@Dao
interface RemoteVideoDao {
    @Query("SELECT * FROM remote_videos WHERE category = :category ORDER BY fetchedAt DESC")
    suspend fun getByCategory(category: String): List<RemoteVideoEntity>

    @Query("SELECT * FROM remote_videos")
    suspend fun getAll(): List<RemoteVideoEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(videos: List<RemoteVideoEntity>)

    @Query("DELETE FROM remote_videos")
    suspend fun clearAll()

    @Query("SELECT MAX(fetchedAt) FROM remote_videos")
    suspend fun lastFetchedAt(): Long?
}
// Register RemoteVideoEntity + RemoteVideoDao in your existing AppDatabase
// (bump the Room version number and add a Migration, or fallbackToDestructiveMigration
// if you don't care about losing this cache table specifically).

// ─────────────────────────────────────────────────────────────
// 3. Repository — fetch-or-cache with a staleness window
// ─────────────────────────────────────────────────────────────
package com.streamx.data.repository

import com.streamx.data.local.RemoteVideoDao
import com.streamx.data.local.RemoteVideoEntity
import com.streamx.data.remote.JsDelivrApi
import java.util.concurrent.TimeUnit

class RemoteVideosRepository(
    private val api: JsDelivrApi,
    private val dao: RemoteVideoDao
) {
    private val staleAfterMs = TimeUnit.HOURS.toMillis(12) // matches jsDelivr CDN cache window

    /** Returns cached data instantly if fresh; otherwise fetches, caches, returns. */
    suspend fun getVideos(forceRefresh: Boolean = false): List<RemoteVideoEntity> {
        val lastFetch = dao.lastFetchedAt() ?: 0L
        val isStale = System.currentTimeMillis() - lastFetch > staleAfterMs

        if (!forceRefresh && !isStale && lastFetch != 0L) {
            val cached = dao.getAll()
            if (cached.isNotEmpty()) return cached
        }

        return try {
            val remote = api.getVideos()
            val now = System.currentTimeMillis()
            val entities = remote.map {
                RemoteVideoEntity(
                    id = it.id,
                    title = it.title,
                    channel = it.channel,
                    thumbnail = it.thumbnail,
                    duration = it.duration,
                    category = it.category,
                    fetchedAt = now
                )
            }
            dao.clearAll()
            dao.insertAll(entities)
            entities
        } catch (e: Exception) {
            // Network/CDN failed — fall back to whatever's cached, even if stale
            dao.getAll()
        }
    }

    suspend fun getByCategory(category: String) = dao.getByCategory(category)
}
