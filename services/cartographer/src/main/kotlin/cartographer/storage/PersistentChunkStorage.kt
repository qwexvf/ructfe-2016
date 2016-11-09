package cartographer.storage

import cartographer.helpers.bytesToInt
import cartographer.helpers.bytesToUuid
import cartographer.helpers.intToBytes
import cartographer.helpers.uuidToBytes
import cartographer.settings.SettingsContainer
import cartographer.settings.StringSetting
import org.apache.logging.log4j.LogManager
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Component
import java.io.*
import java.util.*
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

@Component
@Primary
class PersistentChunkStorage : ChunkStorage, Closeable {
    companion object {
        private val storageFileNameSetting = StringSetting("persistent_storage.file_name", "data/storage")

        private val logger = LogManager.getFormatterLogger()
    }

    private val storageFileStream: OutputStream
    private val cache = ConcurrentHashMap<UUID, ByteArray>()
    private val taskExecutor: ExecutorService

    constructor(settingsContainer: SettingsContainer) {
        val storageFileName = storageFileNameSetting.getValue(settingsContainer)
        val storageFile = getStorageFile(storageFileName)
        populateCacheFromFile(storageFile)
        storageFileStream = FileOutputStream(storageFile)

        taskExecutor = Executors.newSingleThreadExecutor()
    }

    override fun getChunk(id: UUID): ByteArray? {
        return cache[id]
    }

    override fun putChunk(id: UUID, chunk: ByteArray): Boolean {
        if (cache.getOrPut(id, { chunk }) == chunk) {
            logger.debug("Received new chunk with id $id")
            taskExecutor.submit { saveToFile(id, chunk) }
            return true
        }

        logger.debug("Chunk with id $id already exists")
        return false
    }

    override fun close() {
        taskExecutor.shutdownNow()
    }

    private fun getStorageFile(storageFileName: String): File {
        val file = File(storageFileName)
        if (file.exists() || (file.parentFile.mkdirs() && file.createNewFile())) {
            return file
        }

        throw Exception("Failed to open/create file %s".format(file.absoluteFile))
    }

    private fun saveToFile(id: UUID, bytes: ByteArray) {
        storageFileStream.write(uuidToBytes(id))
        storageFileStream.write(intToBytes(bytes.size))
        storageFileStream.write(bytes)
        storageFileStream.flush()
    }

    private fun populateCacheFromFile(storageFile: File) {
        val inputStream = BufferedInputStream(FileInputStream(storageFile))
        val uuidBuffer = ByteArray(16)
        val sizeBuffer = ByteArray(4)
        while (true) {
            if (inputStream.read(uuidBuffer) != uuidBuffer.size || inputStream.read(sizeBuffer) != sizeBuffer.size) {
                return
            }

            val id = bytesToUuid(uuidBuffer)
            val size = bytesToInt(sizeBuffer)
            val bytesBuffer = ByteArray(size)
            if (inputStream.read(bytesBuffer) != bytesBuffer.size) {
                return
            }

            cache.put(id, bytesBuffer)
        }
    }
}