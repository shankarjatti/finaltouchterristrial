#include "tcp_server.h"
#include <iostream>
#include <cstring>
#include <chrono>
#include <iomanip>
#include <sstream>

// POSIX sockets
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

// ─── Helpers ─────────────────────────────────────────────────────────────────
static std::string timestamp_now()
{
    auto now  = std::chrono::system_clock::now();
    auto tt   = std::chrono::system_clock::to_time_t(now);
    auto ms   = std::chrono::duration_cast<std::chrono::milliseconds>(
                    now.time_since_epoch()) % 1000;
    std::ostringstream ss;
    ss << std::put_time(std::localtime(&tt), "%H:%M:%S")
       << "." << std::setw(3) << std::setfill('0') << ms.count();
    return ss.str();
}

static std::string peer_addr(int fd)
{
    sockaddr_in addr{};
    socklen_t   len = sizeof(addr);
    if (getpeername(fd, reinterpret_cast<sockaddr*>(&addr), &len) == 0) {
        char buf[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &addr.sin_addr, buf, sizeof(buf));
        return std::string(buf) + ":" + std::to_string(ntohs(addr.sin_port));
    }
    return "unknown";
}

// ─────────────────────────────────────────────────────────────────────────────
TcpServer::TcpServer(int port, const std::string& band_name)
    : port_(port), band_name_(band_name)
{}

TcpServer::~TcpServer()
{
    stop();
}

bool TcpServer::start()
{
    // ── Create listening socket ───────────────────────────────────────────────
    listen_fd_ = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd_ < 0) {
        std::cerr << "[TCP:" << port_ << "] socket() failed: " << strerror(errno) << "\n";
        return false;
    }

    // SO_REUSEADDR so we can restart quickly
    int opt = 1;
    setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in addr{};
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port        = htons(static_cast<uint16_t>(port_));

    if (bind(listen_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        std::cerr << "[TCP:" << port_ << "] bind() failed: " << strerror(errno) << "\n";
        close(listen_fd_);
        listen_fd_ = -1;
        return false;
    }

    if (listen(listen_fd_, 8) < 0) {
        std::cerr << "[TCP:" << port_ << "] listen() failed: " << strerror(errno) << "\n";
        close(listen_fd_);
        listen_fd_ = -1;
        return false;
    }

    running_       = true;
    accept_thread_ = std::thread(&TcpServer::accept_loop, this);

    std::cout << "[TCP:" << port_ << "] ✔  Listening  band=" << band_name_
              << "  addr=0.0.0.0:" << port_ << "\n";
    return true;
}

void TcpServer::stop()
{
    running_ = false;

    if (listen_fd_ >= 0) {
        shutdown(listen_fd_, SHUT_RDWR);
        close(listen_fd_);
        listen_fd_ = -1;
    }

    if (accept_thread_.joinable())
        accept_thread_.join();

    // Close all clients
    std::lock_guard<std::mutex> lk(clients_mutex_);
    for (int fd : client_fds_) {
        shutdown(fd, SHUT_RDWR);
        close(fd);
    }
    client_fds_.clear();

    std::cout << "[TCP:" << port_ << "] Stopped.\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  Accept loop — runs in its own thread
// ─────────────────────────────────────────────────────────────────────────────
void TcpServer::accept_loop()
{
    while (running_) {
        sockaddr_in client_addr{};
        socklen_t   client_len = sizeof(client_addr);

        int client_fd = accept(listen_fd_,
                               reinterpret_cast<sockaddr*>(&client_addr),
                               &client_len);
        if (client_fd < 0) {
            if (running_)
                std::cerr << "[TCP:" << port_ << "] accept() error: "
                          << strerror(errno) << "\n";
            break;
        }

        // ── TCP_NODELAY — disable Nagle for low latency IQ streaming ─────────
        int flag = 1;
        setsockopt(client_fd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));

        // ── Large send buffer (4 MB) ──────────────────────────────────────────
        int sndbuf = 4 * 1024 * 1024;
        setsockopt(client_fd, SOL_SOCKET, SO_SNDBUF, &sndbuf, sizeof(sndbuf));

        std::string addr = peer_addr(client_fd);

        {
            std::lock_guard<std::mutex> lk(clients_mutex_);
            client_fds_.insert(client_fd);
        }

        // ── CONNECTION VERIFICATION LOG ───────────────────────────────────────
        std::cout << "\n[TCP:" << port_ << "] ╔══ CLIENT CONNECTED ══════════════\n";
        std::cout << "[TCP:" << port_ << "] ║  Time   : " << timestamp_now() << "\n";
        std::cout << "[TCP:" << port_ << "] ║  Client : " << addr << "\n";
        std::cout << "[TCP:" << port_ << "] ║  Band   : " << band_name_ << "\n";
        std::cout << "[TCP:" << port_ << "] ║  Port   : " << port_ << "\n";
        std::cout << "[TCP:" << port_ << "] ║  Total  : " << client_count() << " client(s)\n";
        std::cout << "[TCP:" << port_ << "] ╚══════════════════════════════════\n\n";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  broadcast — send raw bytes to all connected clients
// ─────────────────────────────────────────────────────────────────────────────
int TcpServer::broadcast(const uint8_t* data, size_t len)
{
    std::lock_guard<std::mutex> lk(clients_mutex_);

    std::vector<int> dead;
    int reached = 0;

    for (int fd : client_fds_) {
        ssize_t sent = 0;
        size_t  remaining = len;
        const uint8_t* ptr = data;

        // Keep sending until all bytes are written or error
        while (remaining > 0) {
            ssize_t n = send(fd, ptr, remaining, MSG_NOSIGNAL);
            if (n <= 0) {
                // Client disconnected
                std::string addr = peer_addr(fd);
                std::cout << "\n[TCP:" << port_ << "] ╔══ CLIENT DISCONNECTED ═══════════\n";
                std::cout << "[TCP:" << port_ << "] ║  Time   : " << timestamp_now() << "\n";
                std::cout << "[TCP:" << port_ << "] ║  Client : " << addr << "\n";
                std::cout << "[TCP:" << port_ << "] ║  Band   : " << band_name_ << "\n";
                std::cout << "[TCP:" << port_ << "] ╚══════════════════════════════════\n\n";
                dead.push_back(fd);
                break;
            }
            ptr       += n;
            remaining -= static_cast<size_t>(n);
            sent      += n;
        }

        if (remaining == 0)
            ++reached;
    }

    // Prune dead clients
    for (int fd : dead) {
        close(fd);
        client_fds_.erase(fd);
    }

    return reached;
}

int TcpServer::client_count() const
{
    std::lock_guard<std::mutex> lk(clients_mutex_);
    return static_cast<int>(client_fds_.size());
}

void TcpServer::print_status() const
{
    std::lock_guard<std::mutex> lk(clients_mutex_);
    std::cout << "[TCP:" << port_ << "] Status — band=" << band_name_
              << "  clients=" << client_fds_.size() << "\n";
}
