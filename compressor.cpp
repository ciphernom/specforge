//=============================================================================
// Multithreaded File Compressor/Decompressor
// Version: 2.1.0
//=============================================================================

#include <iostream>
#include <fstream>
#include <thread>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <zlib.h>
#include <memory>
#include <algorithm>
#include <stdexcept>
#include <cstring>
#include <atomic>

// Constants
constexpr size_t CHUNK_SIZE = 1024 * 1024; // 1MB chunks
constexpr uint32_t MAGIC_NUMBER = 0x436F4D50; // "CoMP"
constexpr int DEFAULT_COMPRESSION_LEVEL = Z_DEFAULT_COMPRESSION;

// Custom exception for compression errors
class CompressionError : public std::runtime_error {
public:
    explicit CompressionError(const std::string& message) 
        : std::runtime_error(message) {}
};

// Structure to represent a compression/decompression task
struct CompressionTask {
    std::vector<char> input_chunk;
    std::vector<char> output_chunk;
    size_t chunk_index;
    int compression_level;

    CompressionTask(size_t index, int level = DEFAULT_COMPRESSION_LEVEL)
        : chunk_index(index), compression_level(level) {}
};

// Thread pool for managing compression/decompression workers
class ThreadPool {
private:
    mutable std::mutex mutex;
    std::condition_variable condition;
    std::vector<std::thread> threads;
    std::queue<std::unique_ptr<CompressionTask>> tasks;
    std::vector<std::unique_ptr<CompressionTask>> completed_tasks;
    std::atomic<size_t> active_tasks{0};
    bool stop{false};
    bool compression_mode;

    // Worker thread function
    void worker_thread() {
        while (true) {
            std::unique_ptr<CompressionTask> task;
            
            {
                std::unique_lock<std::mutex> lock(mutex);
                condition.wait(lock, [this] {
                    return stop || !tasks.empty();
                });

                if (stop && tasks.empty()) {
                    return;
                }

                task = std::move(tasks.front());
                tasks.pop();
            }

            active_tasks++;

            try {
                if (compression_mode) {
                    compress_chunk(*task);
                } else {
                    decompress_chunk(*task);
                }

                std::lock_guard<std::mutex> lock(mutex);
                completed_tasks.push_back(std::move(task));
            } catch (...) {
                active_tasks--;
                throw;
            }

            active_tasks--;
            condition.notify_one();
        }
    }

    // Compress a single chunk using zlib
    void compress_chunk(CompressionTask& task) {
        z_stream stream;
        stream.zalloc = Z_NULL;
        stream.zfree = Z_NULL;
        stream.opaque = Z_NULL;

        if (deflateInit2(&stream, task.compression_level, Z_DEFLATED, 15 + 16, 8,
                        Z_DEFAULT_STRATEGY) != Z_OK) {
            throw CompressionError("Failed to initialize deflate");
        }

        stream.next_in = reinterpret_cast<Bytef*>(task.input_chunk.data());
        stream.avail_in = task.input_chunk.size();

        task.output_chunk.resize(deflateBound(&stream, stream.avail_in));
        stream.next_out = reinterpret_cast<Bytef*>(task.output_chunk.data());
        stream.avail_out = task.output_chunk.size();

        if (deflate(&stream, Z_FINISH) != Z_STREAM_END) {
            deflateEnd(&stream);
            throw CompressionError("Deflate failed");
        }

        task.output_chunk.resize(stream.total_out);
        deflateEnd(&stream);
    }

    // Decompress a single chunk using zlib
    void decompress_chunk(CompressionTask& task) {
        z_stream stream;
        stream.zalloc = Z_NULL;
        stream.zfree = Z_NULL;
        stream.opaque = Z_NULL;
        stream.avail_in = 0;
        stream.next_in = Z_NULL;

        if (inflateInit2(&stream, 15 + 16) != Z_OK) {
            throw CompressionError("Failed to initialize inflate");
        }

        stream.next_in = reinterpret_cast<Bytef*>(task.input_chunk.data());
        stream.avail_in = task.input_chunk.size();

        size_t buffer_size = CHUNK_SIZE;
        task.output_chunk.resize(buffer_size);

        while (true) {
            stream.next_out = reinterpret_cast<Bytef*>(task.output_chunk.data() + 
                                                      stream.total_out);
            stream.avail_out = task.output_chunk.size() - stream.total_out;

            int ret = inflate(&stream, Z_NO_FLUSH);
            if (ret == Z_STREAM_END) {
                break;
            }
            if (ret != Z_OK) {
                inflateEnd(&stream);
                throw CompressionError("Inflate failed");
            }

            if (stream.avail_out == 0) {
                task.output_chunk.resize(task.output_chunk.size() * 2);
            }
        }

        task.output_chunk.resize(stream.total_out);
        inflateEnd(&stream);
    }

public:
    ThreadPool(size_t num_threads, bool compress_mode)
        : compression_mode(compress_mode) {
        for (size_t i = 0; i < num_threads; ++i) {
            threads.emplace_back(&ThreadPool::worker_thread, this);
        }
    }

    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lock(mutex);
            stop = true;
        }
        condition.notify_all();
        for (auto& thread : threads) {
            thread.join();
        }
    }

    // Add a task to the queue
    void add_task(std::unique_ptr<CompressionTask> task) {
        std::lock_guard<std::mutex> lock(mutex);
        tasks.push(std::move(task));
        condition.notify_one();
    }

    // Get next completed task in order
    std::unique_ptr<CompressionTask> get_next_completed(size_t expected_index) {
        std::lock_guard<std::mutex> lock(mutex);
        auto it = std::find_if(completed_tasks.begin(), completed_tasks.end(),
            [expected_index](const auto& task) {
                return task->chunk_index == expected_index;
            });

        if (it != completed_tasks.end()) {
            auto task = std::move(*it);
            completed_tasks.erase(it);
            return task;
        }
        return nullptr;
    }

    // Check if all tasks are complete
    bool is_work_complete() const {
        std::lock_guard<std::mutex> lock(mutex);
        return tasks.empty() && active_tasks == 0;
    }
};

// Main compression function
void compress_file_multithreaded(const std::string& input_path, 
                               const std::string& output_path,
                               int compression_level = DEFAULT_COMPRESSION_LEVEL) {
    std::ifstream input(input_path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("Failed to open input file");
    }

    std::ofstream output(output_path, std::ios::binary);
    if (!output) {
        throw std::runtime_error("Failed to open output file");
    }

    // Get input file size
    input.seekg(0, std::ios::end);
    size_t file_size = input.tellg();
    input.seekg(0);

    // Write header
    output.write(reinterpret_cast<const char*>(&MAGIC_NUMBER), sizeof(MAGIC_NUMBER));
    output.write(reinterpret_cast<const char*>(&file_size), sizeof(file_size));

    // Calculate number of chunks
    size_t num_chunks = (file_size + CHUNK_SIZE - 1) / CHUNK_SIZE;
    ThreadPool pool(std::thread::hardware_concurrency(), true);

    // Process chunks
    size_t next_chunk_to_write = 0;
    std::vector<char> chunk_buffer(CHUNK_SIZE);

    for (size_t i = 0; i < num_chunks; ++i) {
        size_t chunk_size = std::min(CHUNK_SIZE, file_size - i * CHUNK_SIZE);
        auto task = std::make_unique<CompressionTask>(i, compression_level);

        task->input_chunk.resize(chunk_size);
        input.read(task->input_chunk.data(), chunk_size);
        if (!input) {
            throw std::runtime_error("Failed to read input chunk");
        }

        pool.add_task(std::move(task));

        // Write completed chunks in order
        while (true) {
            auto completed_task = pool.get_next_completed(next_chunk_to_write);
            if (!completed_task) {
                break;
            }

            // Write chunk size and data
            uint32_t chunk_out_size = completed_task->output_chunk.size();
            output.write(reinterpret_cast<const char*>(&chunk_out_size), 
                        sizeof(chunk_out_size));
            output.write(completed_task->output_chunk.data(), chunk_out_size);

            if (!output) {
                throw std::runtime_error("Failed to write output chunk");
            }

            next_chunk_to_write++;
        }
    }

    // Write any remaining chunks
    while (next_chunk_to_write < num_chunks) {
        auto completed_task = pool.get_next_completed(next_chunk_to_write);
        if (!completed_task) {
            if (pool.is_work_complete()) {
                throw std::runtime_error("Missing compressed chunks");
            }
            std::this_thread::yield();
            continue;
        }

        uint32_t chunk_out_size = completed_task->output_chunk.size();
        output.write(reinterpret_cast<const char*>(&chunk_out_size), 
                    sizeof(chunk_out_size));
        output.write(completed_task->output_chunk.data(), chunk_out_size);

        if (!output) {
            throw std::runtime_error("Failed to write output chunk");
        }

        next_chunk_to_write++;
    }
}

// Main decompression function
void decompress_file_multithreaded(const std::string& input_path, 
                                 const std::string& output_path) {
    std::ifstream input(input_path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("Failed to open input file");
    }

    // Verify magic number
    uint32_t magic;
    input.read(reinterpret_cast<char*>(&magic), sizeof(magic));
    if (magic != MAGIC_NUMBER) {
        throw std::runtime_error("Invalid compressed file format");
    }

    // Read original file size
    size_t original_size;
    input.read(reinterpret_cast<char*>(&original_size), sizeof(original_size));

    std::ofstream output(output_path, std::ios::binary);
    if (!output) {
        throw std::runtime_error("Failed to open output file");
    }

    ThreadPool pool(std::thread::hardware_concurrency(), false);
    size_t next_chunk_to_write = 0;
    size_t total_bytes_written = 0;

    // Process compressed chunks
    size_t chunk_index = 0;
    while (total_bytes_written < original_size && input) {
        // Read compressed chunk size
        uint32_t chunk_size;
        input.read(reinterpret_cast<char*>(&chunk_size), sizeof(chunk_size));
        if (!input) {
            break;
        }

        // Read compressed chunk
        auto task = std::make_unique<CompressionTask>(chunk_index);
        task->input_chunk.resize(chunk_size);
        input.read(task->input_chunk.data(), chunk_size);
        if (!input) {
            throw std::runtime_error("Failed to read compressed chunk");
        }

        pool.add_task(std::move(task));

        // Write completed chunks in order
        while (true) {
            auto completed_task = pool.get_next_completed(next_chunk_to_write);
            if (!completed_task) {
                break;
            }

            output.write(completed_task->output_chunk.data(), 
                        completed_task->output_chunk.size());
            if (!output) {
                throw std::runtime_error("Failed to write decompressed chunk");
            }

            total_bytes_written += completed_task->output_chunk.size();
            next_chunk_to_write++;
        }

        chunk_index++;
    }

    // Write any remaining chunks
    while (total_bytes_written < original_size) {
        auto completed_task = pool.get_next_completed(next_chunk_to_write);
        if (!completed_task) {
            if (pool.is_work_complete()) {
                throw std::runtime_error("Missing decompressed chunks");
            }
            std::this_thread::yield();
            continue;
        }

        output.write(completed_task->output_chunk.data(), 
                    completed_task->output_chunk.size());
        if (!output) {
            throw std::runtime_error("Failed to write decompressed chunk");
        }

        total_bytes_written += completed_task->output_chunk.size();
        next_chunk_to_write++;
    }

    if (total_bytes_written != original_size) {
        throw std::runtime_error("Decompressed size mismatch");
    }
}

int main(int argc, char* argv[]) {
    try {
        if (argc != 4) {
            std::cerr << "Usage: " << argv[0] << " <compress|decompress> "
                     << "<input_file> <output_file>\n";
            return 1;
        }

        std::string command = argv[1];
        std::string input_file = argv[2];
        std::string output_file = argv[3];

        if (command == "compress") {
            compress_file_multithreaded(input_file, output_file);
        } else if (command == "decompress") {
            decompress_file_multithreaded(input_file, output_file);
        } else {
            std::cerr << "Invalid command. Use 'compress' or 'decompress'\n";
            return 1;
        }

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "Unknown error occurred\n";
        return 1;
    }
}
