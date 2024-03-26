#include <iostream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <cstring>
#include <fstream>
#include <unistd.h> // For close()

#define SERVER_IP "localhost"
#define PORT 5000

int main(int argc, char* argv[]) {
    // Check if a filename is provided as a command-line argument
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <filename>" << std::endl;
        return 1;
    }

    const char* filename = argv[1];

    // Create a socket
    int client_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (client_socket == -1) {
        std::cerr << "Error creating socket" << std::endl;
        return 1;
    }

    // Configure server address
    struct sockaddr_in server_address;
    server_address.sin_family = AF_INET;
    server_address.sin_port = htons(PORT);
    if (inet_pton(AF_INET, SERVER_IP, &server_address.sin_addr) == -1) {
        std::cerr << "Error converting IP address" << std::endl;
        close(client_socket);
        return 1;
    }

    // Connect to the server
    if (connect(client_socket, (struct sockaddr*)&server_address, sizeof(server_address)) == -1) {
        std::cerr << "Error connecting to server" << std::endl;
        close(client_socket);
        return 1;
    }

    // Send the filename to the server
    if (send(client_socket, filename, strlen(filename), 0) == -1) {
        std::cerr << "Error sending filename" << std::endl;
        close(client_socket);
        return 1;
    }

    // Open the file for reading
    std::ifstream infile(filename, std::ios::binary);
    if (!infile.is_open()) {
        std::cerr << "Error opening file" << std::endl;
        close(client_socket);
        return 1;
    }

    // Send the file data to the server
    char buffer[1024];
    while (infile.read(buffer, sizeof(buffer)).gcount() > 0) {
        if (send(client_socket, buffer, infile.gcount(), 0) == -1) {
            std::cerr << "Error sending data" << std::endl;
            infile.close();
            close(client_socket);
            return 1;
        }
    }

    infile.close();
    close(client_socket);

    std::cout << "File transfer complete" << std::endl;

    return 0;
}