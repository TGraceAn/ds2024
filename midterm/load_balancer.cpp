#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <cstring>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <curl/curl.h>

// List of Reddit server addresses
std::vector<std::string> redditServers = {"https://www.reddit.com/r/subreddit1", "https://www.reddit.com/r/subreddit2", "https://www.reddit.com/r/subreddit3"};

// Load balancer server address and port
std::string lbAddress = "192.168.1.200";
int lbPort = 8080;

// Callback function for libcurl
static size_t writeCallback(char *contents, size_t size, size_t nmemb, void *userp) {
    ((std::string*)userp)->append(contents, size * nmemb);
    return size * nmemb;
}

int main() {
    // Initialize libcurl
    curl_global_init(CURL_GLOBAL_DEFAULT);

    // Create a socket for the load balancer
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        std::cerr << "Error creating socket" << std::endl;
        return 1;
    }

    // Bind the socket to the load balancer address and port
    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = inet_addr(lbAddress.c_str());
    serv_addr.sin_port = htons(lbPort);
    if (bind(sockfd, (struct sockaddr *) &serv_addr, sizeof(serv_addr)) < 0) {
        std::cerr << "Error binding socket" << std::endl;
        return 1;
    }

    // Listen for incoming connections
    if (listen(sockfd, 5) < 0) {
        std::cerr << "Error listening on socket" << std::endl;
        return 1;
    }

    std::cout << "Load balancer listening on " << lbAddress << ":" << lbPort << std::endl;

    while (true) {
        // Wait for a connection
        int clientfd = accept(sockfd, NULL, NULL);
        if (clientFd < 0) {
            std::cerr << "Error accepting connection" << std::endl;
            continue;
        }

        std::cout << "Received connection" << std::endl;

        // Choose a Reddit server
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, redditServers.size() - 1);
        int idx = dis(gen);
        std::string redditServer = redditServers[idx];
        std::cout << "Forwarding request to Reddit server: " << redditServer << std::endl;

        // Forward the request to the Reddit server
        CURL* curl = curl_easy_init();
        if (curl) {
            std::string response;
            curl_easy_setopt(curl, CURLOPT_URL, redditServer.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
            CURLcode res = curl_easy_perform(curl);
            if (res != CURLE_OK) {
                std::cerr << "Error forwarding request to Reddit server: " << curl_easy_strerror(res) << std::endl;
                send(clientFd, "Error: Could not connect to Reddit server.", 40, 0);
            } else {
                send(clientFd, response.c_str(), response.length(), 0);
            }
            curl_easy_cleanup(curl);
        }

        // Close the client connection
        close(clientFd);
    }
    

    // Clean up
    close(sockfd);
    curl_global_cleanup();
    return 0;
}