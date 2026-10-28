#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <set>

// ─────────────────────────────────────────────────────────────────────────────
//  TcpServer
//
//  Listens on a single port. Accepts multiple clients.
//  broadcast() sends the same raw bytes to all connected clients.
//  Disconnected clients are pruned automatically.
//
//  Connection verification:
//   - Logs every connect / disconnect with client IP and timestamp
//   - Reports client count on each broadcast
//   - Provides client_count() for status checks
// ─────────────────────────────────────────────────────────────────────────────
class TcpServer {
public:
    explicit TcpServer(int port, const std::string& band_name);
    ~TcpServer();

    // Start listening thread (non-blocking)
    bool start();

    // Stop listening, close all client sockets
    void stop();

    // Send raw bytes to all connected clients; returns number of clients reached
    int broadcast(const uint8_t* data, size_t len);

    // Number of currently connected clients
    int  client_count() const;
    int  port()         const { return port_; }
    const std::string& band() const { return band_name_; }

    // Print current connection status table
    void print_status() const;

private:
    void accept_loop();

    int                port_;
    std::string        band_name_;
    int                listen_fd_{-1};

    mutable std::mutex  clients_mutex_;
    std::set<int>       client_fds_;

    // drop accounting for slow clients (see broadcast(): sends are
    // non-blocking so a stalled consumer cannot freeze the burst scheduler)
    mutable size_t      dropped_bytes_{0};
    mutable size_t      drop_events_{0};

    std::thread         accept_thread_;
    std::atomic<bool>   running_{false};
};
