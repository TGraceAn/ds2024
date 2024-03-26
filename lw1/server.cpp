#include <iostream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <cstring>
#include <fstream>
#include <unistd.h> // For close()

#define PORT 5000
#define MAX_FILENAME_LEN 1024

int main() {
    // Create a socket
    int server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server_socket == -1) {
        std::cerr << "Error creating socket" << std::endl;
        return 1;
    }

    // Configure server address
    struct sockaddr_in server_address;
    server_address.sin_family = AF_INET;
    server_address.sin_addr.s_addr = INADDR_ANY;
    server_address.sin_port = htons(PORT);

    // Bind socket to address
    if (bind(server_socket, (struct sockaddr*)&server_address, sizeof(server_address)) == -1) {
        std::cerr << "Error binding socket" << std::endl;
        close(server_socket);
        return 1;
    }

    // Listen for incoming connections
    if (listen(server_socket, 1) == -1) {
        std::cerr << "Error listening for connections" << std::endl;
        close(server_socket);
        return 1;
    }

    std::cout << "Server listening on port " << PORT << std::endl;

    // Accept a connection
    int client_socket;
    struct sockaddr_in client_address;
    socklen_t client_address_size = sizeof(client_address);
    client_socket = accept(server_socket, (struct sockaddr*)&client_address, &client_address_size);
    if (client_socket == -1) {
        std::cerr << "Error accepting connection" << std::endl;
        close(server_socket);
        return 1;
    }

    std::cout << "Connected by " << inet_ntoa(client_address.sin_addr) << std::endl;

    // Receive the filename from the client
    char filename[MAX_FILENAME_LEN];
    if (recv(client_socket, filename, MAX_FILENAME_LEN, 0) == -1) {
        std::cerr << "Error receiving filename" << std::endl;
        close(client_socket);
        close(server_socket);
        return 1;
    }

    // Open file for writing
    std::ofstream outfile(filename, std::ios::binary);
    if (!outfile.is_open()) {
        std::cerr << "Error opening file" << std::endl;
        close(client_socket);
        close(server_socket);
        return 1;
    }

    // Receive file data in loop
    char buffer[1024];
    int bytes_received;
    while ((bytes_received = recv(client_socket, buffer, sizeof(buffer), 0)) > 0) {
        outfile.write(buffer, bytes_received);
    }

    if (bytes_received == -1) {
        std::cerr << "Error receiving data" << std::endl;
    }

    outfile.close();
    close(client_socket);
    close(server_socket);

    std::cout << "File transfer complete" << std::endl;

    return 0;
}