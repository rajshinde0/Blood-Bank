#include <iostream>
#include <fstream>
#include <string>
#include <iomanip>
#include <vector>
#include <queue>
#include <limits>
#include <climits>
#include <algorithm>
#include <list>
#include <unordered_map>
#include <cctype>
#include <stack>
#include <ctime>
using namespace std;

struct Donor
{
    int id;
    string name, bloodGroup, city, phone;
    Donor *next;
};

struct Patient
{
    int id;
    string name, bloodGroupRequired, city, phone;
    int age;
    int urgency; // 1 = Critical, 2 = Urgent, 3 = Normal
    time_t deadline;  // Deadline timestamp for patient service
    time_t arrivalTime;  // When patient was added to queue
    
    Patient() : id(0), age(0), urgency(3), deadline(0), arrivalTime(0) {}
};

// ---------- AVL Tree for Donor Name Search (Self-Balancing) ----------

struct AVLNode
{
    string donorName;
    int donorID;
    int height;
    AVLNode *left;
    AVLNode *right;

    AVLNode(string name, int id) : donorName(name), donorID(id), height(1), left(nullptr), right(nullptr) {}
};

class DonorBST
{
private:
    AVLNode *root;

    int getHeight(AVLNode *node)
    {
        return node ? node->height : 0;
    }

    int getBalanceFactor(AVLNode *node)
    {
        return node ? getHeight(node->left) - getHeight(node->right) : 0;
    }

    void updateHeight(AVLNode *node)
    {
        if (node)
        {
            node->height = 1 + max(getHeight(node->left), getHeight(node->right));
        }
    }

    AVLNode *rightRotate(AVLNode *y)
    {
        AVLNode *x = y->left;
        AVLNode *T2 = x->right;

        x->right = y;
        y->left = T2;

        updateHeight(y);
        updateHeight(x);

        return x;
    }

    AVLNode *leftRotate(AVLNode *x)
    {
        AVLNode *y = x->right;
        AVLNode *T2 = y->left;

        y->left = x;
        x->right = T2;

        updateHeight(x);
        updateHeight(y);

        return y;
    }

    AVLNode *balance(AVLNode *node)
    {
        updateHeight(node);
        int balanceFactor = getBalanceFactor(node);

        // Left-Left Case
        if (balanceFactor > 1 && getBalanceFactor(node->left) >= 0)
        {
            return rightRotate(node);
        }

        // Left-Right Case
        if (balanceFactor > 1 && getBalanceFactor(node->left) < 0)
        {
            node->left = leftRotate(node->left);
            return rightRotate(node);
        }

        // Right-Right Case
        if (balanceFactor < -1 && getBalanceFactor(node->right) <= 0)
        {
            return leftRotate(node);
        }

        // Right-Left Case
        if (balanceFactor < -1 && getBalanceFactor(node->right) > 0)
        {
            node->right = rightRotate(node->right);
            return leftRotate(node);
        }

        return node;
    }

    AVLNode *insertHelper(AVLNode *node, string name, int id)
    {
        if (node == nullptr)
        {
            return new AVLNode(name, id);
        }

        if (name < node->donorName)
        {
            node->left = insertHelper(node->left, name, id);
        }
        else if (name > node->donorName)
        {
            node->right = insertHelper(node->right, name, id);
        }
        else
        {
            return node; // Duplicate names not allowed
        }

        return balance(node);
    }

    AVLNode *searchHelper(AVLNode *node, string name)
    {
        if (node == nullptr)
        {
            return nullptr;
        }

        if (name == node->donorName)
        {
            return node;
        }
        else if (name < node->donorName)
        {
            return searchHelper(node->left, name);
        }
        else
        {
            return searchHelper(node->right, name);
        }
    }

public:
    DonorBST() : root(nullptr) {}

    void insert(string name, int id)
    {
        root = insertHelper(root, name, id);
    }

    int search(string name)
    {
        AVLNode *result = searchHelper(root, name);
        if (result != nullptr)
        {
            return result->donorID;
        }
        return -1;
    }
};

// ---------- Blood Compatibility Graph ----------

class BloodCompatibilityGraph
{
private:
    static const int NUM_BLOOD_TYPES = 8;
    bool adjacencyMatrix[NUM_BLOOD_TYPES][NUM_BLOOD_TYPES];
    string bloodTypes[NUM_BLOOD_TYPES] = {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"};

    int getIndex(string bloodGroup)
    {
        for (int i = 0; i < NUM_BLOOD_TYPES; i++)
        {
            if (bloodTypes[i] == bloodGroup)
            {
                return i;
            }
        }
        return -1;
    }

public:
    BloodCompatibilityGraph()
    {
        for (int i = 0; i < NUM_BLOOD_TYPES; i++)
        {
            for (int j = 0; j < NUM_BLOOD_TYPES; j++)
            {
                adjacencyMatrix[i][j] = false;
            }
        }

        // O- (index 0) - Universal donor
        for (int j = 0; j < NUM_BLOOD_TYPES; j++)
        {
            adjacencyMatrix[0][j] = true;
        }

        // O+ (index 1)
        adjacencyMatrix[1][1] = true;
        adjacencyMatrix[1][3] = true;
        adjacencyMatrix[1][5] = true;
        adjacencyMatrix[1][7] = true;

        // A- (index 2)
        adjacencyMatrix[2][2] = true;
        adjacencyMatrix[2][3] = true;
        adjacencyMatrix[2][6] = true;
        adjacencyMatrix[2][7] = true;

        // A+ (index 3)
        adjacencyMatrix[3][3] = true;
        adjacencyMatrix[3][7] = true;

        // B- (index 4)
        adjacencyMatrix[4][4] = true;
        adjacencyMatrix[4][5] = true;
        adjacencyMatrix[4][6] = true;
        adjacencyMatrix[4][7] = true;

        // B+ (index 5)
        adjacencyMatrix[5][5] = true;
        adjacencyMatrix[5][7] = true;

        // AB- (index 6)
        adjacencyMatrix[6][6] = true;
        adjacencyMatrix[6][7] = true;

        // AB+ (index 7)
        adjacencyMatrix[7][7] = true;
    }

    bool isCompatible(string donorGroup, string patientGroup)
    {
        int donorIndex = getIndex(donorGroup);
        int patientIndex = getIndex(patientGroup);

        if (donorIndex == -1 || patientIndex == -1)
        {
            return false;
        }

        return adjacencyMatrix[donorIndex][patientIndex];
    }

    void displayCompatibilityMatrix()
    {
        cout << "\n=== Blood Compatibility Matrix ===\n";
        cout << "Rows = Donor, Columns = Recipient\n\n";
        cout << setw(8) << " ";
        for (int j = 0; j < NUM_BLOOD_TYPES; j++)
        {
            cout << setw(6) << bloodTypes[j];
        }
        cout << endl;

        for (int i = 0; i < NUM_BLOOD_TYPES; i++)
        {
            cout << setw(6) << bloodTypes[i] << "  ";
            for (int j = 0; j < NUM_BLOOD_TYPES; j++)
            {
                cout << setw(6) << (adjacencyMatrix[i][j] ? "✓" : "✗");
            }
            cout << endl;
        }
        cout << endl;
    }
    
    // ---------- BFS and DFS Traversal on Compatibility Graph ----------
    
    void BFS(string startBloodType)
    {
        int startIndex = getIndex(startBloodType);
        if (startIndex == -1)
        {
            cout << "Invalid blood type!\n";
            return;
        }
        
        vector<bool> visited(NUM_BLOOD_TYPES, false);
        queue<int> q;
        
        q.push(startIndex);
        visited[startIndex] = true;
        
        cout << "\n=== BFS Traversal from " << startBloodType << " ===\n";
        cout << "Blood types that " << startBloodType << " can donate to (in BFS order):\n";
        
        while (!q.empty())
        {
            int current = q.front();
            q.pop();
            
            cout << bloodTypes[current] << " ";
            
            // Visit all adjacent nodes (compatible blood types)
            for (int j = 0; j < NUM_BLOOD_TYPES; j++)
            {
                if (adjacencyMatrix[current][j] && !visited[j])
                {
                    visited[j] = true;
                    q.push(j);
                }
            }
        }
        cout << "\n\n";
    }
    
    void DFSHelper(int current, vector<bool> &visited)
    {
        visited[current] = true;
        cout << bloodTypes[current] << " ";
        
        // Visit all adjacent nodes
        for (int j = 0; j < NUM_BLOOD_TYPES; j++)
        {
            if (adjacencyMatrix[current][j] && !visited[j])
            {
                DFSHelper(j, visited);
            }
        }
    }
    
    void DFS(string startBloodType)
    {
        int startIndex = getIndex(startBloodType);
        if (startIndex == -1)
        {
            cout << "Invalid blood type!\n";
            return;
        }
        
        vector<bool> visited(NUM_BLOOD_TYPES, false);
        
        cout << "\n=== DFS Traversal from " << startBloodType << " ===\n";
        cout << "Blood types that " << startBloodType << " can donate to (in DFS order):\n";
        
        DFSHelper(startIndex, visited);
        cout << "\n\n";
    }
    
    void findAllPaths(int source, int dest, vector<int> &path, vector<vector<int>> &allPaths)
    {
        path.push_back(source);
        
        if (source == dest)
        {
            allPaths.push_back(path);
        }
        else
        {
            for (int i = 0; i < NUM_BLOOD_TYPES; i++)
            {
                if (adjacencyMatrix[source][i])
                {
                    // Check if not already in path (avoid cycles)
                    bool inPath = false;
                    for (int node : path)
                    {
                        if (node == i)
                        {
                            inPath = true;
                            break;
                        }
                    }
                    
                    if (!inPath)
                    {
                        findAllPaths(i, dest, path, allPaths);
                    }
                }
            }
        }
        
        path.pop_back();
    }
    
    void displayAllCompatibilityPaths(string donorType, string patientType)
    {
        int source = getIndex(donorType);
        int dest = getIndex(patientType);
        
        if (source == -1 || dest == -1)
        {
            cout << "Invalid blood type!\n";
            return;
        }
        
        vector<vector<int>> allPaths;
        vector<int> path;
        
        findAllPaths(source, dest, path, allPaths);
        
        cout << "\n=== All Compatibility Paths from " << donorType << " to " << patientType << " ===\n";
        
        if (allPaths.empty())
        {
            cout << "No compatibility path exists!\n";
        }
        else
        {
            cout << "Found " << allPaths.size() << " path(s):\n";
            for (size_t i = 0; i < allPaths.size(); i++)
            {
                cout << "Path " << (i + 1) << ": ";
                for (size_t j = 0; j < allPaths[i].size(); j++)
                {
                    cout << bloodTypes[allPaths[i][j]];
                    if (j < allPaths[i].size() - 1) cout << " -> ";
                }
                cout << endl;
            }
        }
        cout << endl;
    }
};

// ---------- Trie (Prefix Tree) for Autocomplete ----------

struct TrieNode
{
    TrieNode *children[26];
    bool isEndOfWord;
    vector<int> donorIDs;  // Store all donor IDs with this prefix
    
    TrieNode()
    {
        isEndOfWord = false;
        for (int i = 0; i < 26; i++)
        {
            children[i] = nullptr;
        }
    }
};

class DonorTrie
{
private:
    TrieNode *root;
    
    int getIndex(char c)
    {
        return tolower(c) - 'a';
    }
    
    void collectAllNames(TrieNode *node, string prefix, vector<pair<string, int>> &results)
    {
        if (node == nullptr) return;
        
        if (node->isEndOfWord)
        {
            for (int id : node->donorIDs)
            {
                results.push_back({prefix, id});
            }
        }
        
        for (int i = 0; i < 26; i++)
        {
            if (node->children[i] != nullptr)
            {
                char ch = 'a' + i;
                collectAllNames(node->children[i], prefix + ch, results);
            }
        }
    }
    
public:
    DonorTrie()
    {
        root = new TrieNode();
    }
    
    void insert(string name, int donorID)
    {
        TrieNode *current = root;
        
        // Convert to lowercase for case-insensitive search
        for (char c : name)
        {
            if (isalpha(c))
            {
                int index = getIndex(c);
                if (current->children[index] == nullptr)
                {
                    current->children[index] = new TrieNode();
                }
                current = current->children[index];
            }
        }
        
        current->isEndOfWord = true;
        current->donorIDs.push_back(donorID);
    }
    
    vector<pair<string, int>> searchPrefix(string prefix)
    {
        vector<pair<string, int>> results;
        TrieNode *current = root;
        
        // Navigate to the prefix
        for (char c : prefix)
        {
            if (!isalpha(c)) continue;
            
            int index = getIndex(c);
            if (current->children[index] == nullptr)
            {
                return results;  // Prefix not found
            }
            current = current->children[index];
        }
        
        // Collect all names with this prefix
        collectAllNames(current, prefix, results);
        return results;
    }
    
    bool search(string name)
    {
        TrieNode *current = root;
        
        for (char c : name)
        {
            if (!isalpha(c)) continue;
            
            int index = getIndex(c);
            if (current->children[index] == nullptr)
            {
                return false;
            }
            current = current->children[index];
        }
        
        return current->isEndOfWord;
    }
};

// ---------- LRU Cache for Donor Performance Optimization ----------

class LRUCache
{
private:
    int capacity;
    list<pair<int, Donor*>> dll;  // Doubly linked list: {donorID, Donor*}
    unordered_map<int, list<pair<int, Donor*>>::iterator> cache;
    
public:
    LRUCache(int cap) : capacity(cap) {}
    
    Donor* get(int donorID)
    {
        if (cache.find(donorID) == cache.end())
        {
            return nullptr;  // Cache miss
        }
        
        // Move to front (most recently used)
        auto it = cache[donorID];
        pair<int, Donor*> item = *it;
        dll.erase(it);
        dll.push_front(item);
        cache[donorID] = dll.begin();
        
        return item.second;
    }
    
    void put(int donorID, Donor* donor)
    {
        // If already exists, update and move to front
        if (cache.find(donorID) != cache.end())
        {
            dll.erase(cache[donorID]);
        }
        else if (dll.size() >= (size_t)capacity)
        {
            // Remove least recently used (back of list)
            int oldID = dll.back().first;
            dll.pop_back();
            cache.erase(oldID);
        }
        
        // Add to front (most recently used)
        dll.push_front({donorID, donor});
        cache[donorID] = dll.begin();
    }
    
    void displayCache()
    {
        if (dll.empty())
        {
            cout << "Cache is empty.\n";
            return;
        }
        
        cout << "\n=== LRU Cache Contents (Most Recent First) ===\n";
        for (auto &item : dll)
        {
            Donor *d = item.second;
            cout << "ID: " << d->id << " | Name: " << d->name 
                 << " | Blood: " << d->bloodGroup << endl;
        }
    }
};

// ---------- Union-Find (Disjoint Set) for Donor Networks ----------

class DonorUnionFind
{
private:
    unordered_map<int, int> parent;
    unordered_map<int, int> rank;
    
public:
    void makeSet(int donorID)
    {
        if (parent.find(donorID) == parent.end())
        {
            parent[donorID] = donorID;
            rank[donorID] = 0;
        }
    }
    
    int find(int x)
    {
        if (parent.find(x) == parent.end())
        {
            makeSet(x);
        }
        
        if (parent[x] != x)
        {
            parent[x] = find(parent[x]);  // Path compression
        }
        return parent[x];
    }
    
    void unionSets(int x, int y)
    {
        int rootX = find(x);
        int rootY = find(y);
        
        if (rootX == rootY) return;
        
        // Union by rank
        if (rank[rootX] < rank[rootY])
        {
            parent[rootX] = rootY;
        }
        else if (rank[rootX] > rank[rootY])
        {
            parent[rootY] = rootX;
        }
        else
        {
            parent[rootY] = rootX;
            rank[rootX]++;
        }
    }
    
    bool areConnected(int x, int y)
    {
        return find(x) == find(y);
    }
    
    void displayNetworks()
    {
        unordered_map<int, vector<int>> networks;
        
        // Group donors by their root
        for (auto &p : parent)
        {
            int donorID = p.first;
            int root = find(donorID);
            networks[root].push_back(donorID);
        }
        
        cout << "\n=== Donor Networks (Connected Components) ===\n";
        int networkNum = 1;
        for (auto &network : networks)
        {
            cout << "Network " << networkNum++ << ": ";
            for (int id : network.second)
            {
                cout << id << " ";
            }
            cout << endl;
        }
    }
};

// ---------- Dijkstra's Algorithm for Blood Delivery Optimization ----------

struct Edge
{
    int destination;
    int distance;
    
    Edge(int dest, int dist) : destination(dest), distance(dist) {}
};

// ---------- Segment Tree for Blood Inventory Range Queries ----------

class InventorySegmentTree
{
private:
    vector<int> tree;
    vector<int> inventory;  // Original inventory data
    int n;

    void buildTree(int node, int start, int end)
    {
        if (start == end)
        {
            tree[node] = inventory[start];
        }
        else
        {
            int mid = (start + end) / 2;
            int leftChild = 2 * node + 1;
            int rightChild = 2 * node + 2;
            
            buildTree(leftChild, start, mid);
            buildTree(rightChild, mid + 1, end);
            
            tree[node] = tree[leftChild] + tree[rightChild];
        }
    }

    int queryRange(int node, int start, int end, int l, int r)
    {
        // No overlap
        if (r < start || l > end)
        {
            return 0;
        }
        
        // Complete overlap
        if (l <= start && end <= r)
        {
            return tree[node];
        }
        
        // Partial overlap
        int mid = (start + end) / 2;
        int leftChild = 2 * node + 1;
        int rightChild = 2 * node + 2;
        
        int leftSum = queryRange(leftChild, start, mid, l, r);
        int rightSum = queryRange(rightChild, mid + 1, end, l, r);
        
        return leftSum + rightSum;
    }

    void updateTree(int node, int start, int end, int idx, int value)
    {
        if (start == end)
        {
            tree[node] = value;
            inventory[idx] = value;
        }
        else
        {
            int mid = (start + end) / 2;
            int leftChild = 2 * node + 1;
            int rightChild = 2 * node + 2;
            
            if (idx <= mid)
            {
                updateTree(leftChild, start, mid, idx, value);
            }
            else
            {
                updateTree(rightChild, mid + 1, end, idx, value);
            }
            
            tree[node] = tree[leftChild] + tree[rightChild];
        }
    }

public:
    InventorySegmentTree(vector<int> data)
    {
        inventory = data;
        n = data.size();
        tree.resize(4 * n, 0);  // Segment tree needs 4*n space
        if (n > 0)
        {
            buildTree(0, 0, n - 1);
        }
    }

    // Get total blood units in range [l, r]
    int getRangeSum(int l, int r)
    {
        if (n == 0 || l < 0 || r >= n || l > r)
        {
            return 0;
        }
        return queryRange(0, 0, n - 1, l, r);
    }

    // Update inventory at index idx to new value
    void updateInventory(int idx, int value)
    {
        if (idx >= 0 && idx < n)
        {
            updateTree(0, 0, n - 1, idx, value);
        }
    }

    void displayInventory()
    {
        cout << "\n=== Blood Inventory (Segment Tree) ===\n";
        for (int i = 0; i < n; i++)
        {
            cout << "Day " << (i + 1) << ": " << inventory[i] << " units\n";
        }
        cout << "Total units: " << getRangeSum(0, n - 1) << "\n";
    }
};

// ---------- Minimum Spanning Tree (Kruskal's Algorithm) ----------

struct MSTEdge
{
    int src, dest, weight;
    
    MSTEdge(int s, int d, int w) : src(s), dest(d), weight(w) {}
    
    bool operator<(const MSTEdge& other) const
    {
        return weight < other.weight;
    }
};

class BloodBankMST
{
private:
    int numBanks;
    vector<MSTEdge> edges;
    vector<string> bankNames;
    
    // Union-Find helper functions for Kruskal's
    int findParent(vector<int>& parent, int x)
    {
        if (parent[x] != x)
        {
            parent[x] = findParent(parent, parent[x]);  // Path compression
        }
        return parent[x];
    }
    
    void unionSets(vector<int>& parent, vector<int>& rank, int x, int y)
    {
        int xRoot = findParent(parent, x);
        int yRoot = findParent(parent, y);
        
        if (rank[xRoot] < rank[yRoot])
        {
            parent[xRoot] = yRoot;
        }
        else if (rank[xRoot] > rank[yRoot])
        {
            parent[yRoot] = xRoot;
        }
        else
        {
            parent[yRoot] = xRoot;
            rank[xRoot]++;
        }
    }

public:
    BloodBankMST(int banks) : numBanks(banks)
    {
        bankNames.resize(banks);
    }
    
    void addBank(int index, string name)
    {
        if (index >= 0 && index < numBanks)
        {
            bankNames[index] = name;
        }
    }
    
    void addConnection(int bank1, int bank2, int cost)
    {
        edges.push_back(MSTEdge(bank1, bank2, cost));
    }
    
    vector<MSTEdge> kruskalMST()
    {
        vector<MSTEdge> result;
        
        // Sort edges by weight
        sort(edges.begin(), edges.end());
        
        // Initialize Union-Find
        vector<int> parent(numBanks);
        vector<int> rank(numBanks, 0);
        
        for (int i = 0; i < numBanks; i++)
        {
            parent[i] = i;
        }
        
        // Kruskal's algorithm
        int edgeCount = 0;
        for (const MSTEdge& edge : edges)
        {
            if (edgeCount >= numBanks - 1) break;
            
            int srcParent = findParent(parent, edge.src);
            int destParent = findParent(parent, edge.dest);
            
            // If including this edge doesn't form a cycle
            if (srcParent != destParent)
            {
                result.push_back(edge);
                unionSets(parent, rank, srcParent, destParent);
                edgeCount++;
            }
        }
        
        return result;
    }
    
    void displayMST()
    {
        cout << "\n=== Minimum Spanning Tree (Blood Bank Network) ===\n";
        vector<MSTEdge> mst = kruskalMST();
        
        if (mst.empty())
        {
            cout << "No MST found. Add more connections.\n";
            return;
        }
        
        int totalCost = 0;
        cout << "\nOptimal connections to minimize cost:\n";
        cout << "----------------------------------------\n";
        
        for (const MSTEdge& edge : mst)
        {
            cout << bankNames[edge.src] << " <--> " 
                 << bankNames[edge.dest] << " (Cost: " 
                 << edge.weight << ")\n";
            totalCost += edge.weight;
        }
        
        cout << "----------------------------------------\n";
        cout << "Total Minimum Cost: " << totalCost << "\n";
        cout << "Number of connections: " << mst.size() << "\n";
    }
    
    int getTotalCost()
    {
        vector<MSTEdge> mst = kruskalMST();
        int total = 0;
        for (const MSTEdge& edge : mst)
        {
            total += edge.weight;
        }
        return total;
    }
};

class BloodDeliveryGraph
{
private:
    int numLocations;
    vector<vector<Edge>> adjList;
    vector<string> locationNames;

public:
    BloodDeliveryGraph(int V) : numLocations(V)
    {
        adjList.resize(V);
        locationNames.resize(V);
    }

    void addLocation(int index, string name)
    {
        if (index >= 0 && index < numLocations)
        {
            locationNames[index] = name;
        }
    }

    void addRoute(int from, int to, int distance)
    {
        if (from >= 0 && from < numLocations && to >= 0 && to < numLocations)
        {
            adjList[from].push_back(Edge(to, distance));
            adjList[to].push_back(Edge(from, distance)); // Bidirectional
        }
    }

    vector<int> dijkstra(int source, int destination)
    {
        vector<int> dist(numLocations, INT_MAX);
        vector<int> parent(numLocations, -1);
        vector<bool> visited(numLocations, false);

        priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> pq;

        dist[source] = 0;
        pq.push({0, source});

        while (!pq.empty())
        {
            int u = pq.top().second;
            pq.pop();

            if (visited[u]) continue;
            visited[u] = true;

            for (const Edge &edge : adjList[u])
            {
                int v = edge.destination;
                int weight = edge.distance;

                if (dist[u] + weight < dist[v])
                {
                    dist[v] = dist[u] + weight;
                    parent[v] = u;
                    pq.push({dist[v], v});
                }
            }
        }

        vector<int> path;
        if (dist[destination] == INT_MAX)
        {
            return path; // No path found
        }

        for (int v = destination; v != -1; v = parent[v])
        {
            path.push_back(v);
        }
        reverse(path.begin(), path.end());

        return path;
    }

    void displayShortestPath(int source, int destination)
    {
        vector<int> path = dijkstra(source, destination);

        if (path.empty())
        {
            cout << "No route available from " << locationNames[source]
                 << " to " << locationNames[destination] << endl;
            return;
        }

        cout << "\n=== Shortest Blood Delivery Route ===\n";
        cout << "From: " << locationNames[source] << " (Location " << source << ")\n";
        cout << "To: " << locationNames[destination] << " (Location " << destination << ")\n\n";
        cout << "Route: ";

        int totalDistance = 0;
        for (size_t i = 0; i < path.size(); i++)
        {
            cout << locationNames[path[i]];
            if (i < path.size() - 1)
            {
                cout << " -> ";
                
                // Calculate distance between consecutive nodes
                for (const Edge &edge : adjList[path[i]])
                {
                    if (edge.destination == path[i + 1])
                    {
                        totalDistance += edge.distance;
                        break;
                    }
                }
            }
        }

        cout << "\nTotal Distance: " << totalDistance << " km\n";
    }

    void displayAllRoutes()
    {
        cout << "\n=== Blood Bank Network Routes ===\n";
        for (int i = 0; i < numLocations; i++)
        {
            cout << locationNames[i] << " (Location " << i << ") connects to:\n";
            if (adjList[i].empty())
            {
                cout << "  No connections\n";
            }
            else
            {
                for (const Edge &edge : adjList[i])
                {
                    cout << "  -> " << locationNames[edge.destination]
                         << " (Distance: " << edge.distance << " km)\n";
                }
            }
            cout << endl;
        }
    }
};

// ---------- Priority Queue (Min-Heap) for Patients with Dynamic Allocation ----------

#include <vector>

class PatientQueue
{
private:
    vector<Patient> heap;  // Dynamic allocation using vector

    // Compare patients: urgency first, then deadline (Earliest Deadline First)
    bool hasHigherPriority(const Patient& p1, const Patient& p2)
    {
        // Lower urgency number = higher priority (1 is most critical)
        if (p1.urgency != p2.urgency)
        {
            return p1.urgency < p2.urgency;
        }
        
        // If urgency is same, earlier deadline has priority
        // If no deadline set (0), treat as lowest priority
        if (p1.deadline == 0 && p2.deadline == 0)
        {
            return false;  // Equal priority
        }
        if (p1.deadline == 0) return false;  // p2 has deadline, higher priority
        if (p2.deadline == 0) return true;   // p1 has deadline, higher priority
        
        return p1.deadline < p2.deadline;  // Earlier deadline wins
    }

    void bubbleUp(int index)
    {
        if (index == 0) return;
        
        int parentIndex = (index - 1) / 2;
        
        if (hasHigherPriority(heap[index], heap[parentIndex]))
        {
            swap(heap[index], heap[parentIndex]);
            bubbleUp(parentIndex);
        }
    }

    void bubbleDown(int index)
    {
        int size = heap.size();
        int leftChild = 2 * index + 1;
        int rightChild = 2 * index + 2;
        int smallest = index;

        if (leftChild < (int)heap.size() && hasHigherPriority(heap[leftChild], heap[smallest]))
        {
            smallest = leftChild;
        }

        if (rightChild < (int)heap.size() && hasHigherPriority(heap[rightChild], heap[smallest]))
        {
            smallest = rightChild;
        }

        if (smallest != index)
        {
            swap(heap[index], heap[smallest]);
            bubbleDown(smallest);
        }
    }

public:
    PatientQueue() {}  // No initialization needed for vector

    bool isEmpty()
    {
        return heap.empty();
    }

    bool isFull()
    {
        return false;  // Vector can grow dynamically, never full
    }

    void enqueue(Patient p)
    {
        heap.push_back(p);
        bubbleUp(heap.size() - 1);
        cout << "Patient added to priority queue.\n";
    }

    Patient dequeue()
    {
        if (isEmpty())
        {
            cout << "No patients in queue!\n";
            return Patient();
        }

        Patient mostCritical = heap[0];
        heap[0] = heap.back();
        heap.pop_back();
        
        if (!heap.empty())
        {
            bubbleDown(0);
        }

        return mostCritical;
    }

    Patient peek()
    {
        if (isEmpty())
        {
            cout << "No patients in queue!\n";
            return Patient();
        }
        return heap[0];
    }

    void displayQueue()
    {
        if (isEmpty())
        {
            cout << "No patients in queue.\n";
            return;
        }

        cout << left << setw(10) << "ID" << setw(20) << "Name" << setw(6) << "Age"
             << setw(15) << "Phone" << setw(15) << "City"
             << setw(10) << "BloodReq" << setw(12) << "Urgency" << setw(20) << "Deadline" << endl;
        cout << "----------------------------------------------------------------------------------------------------\\n";

        time_t now = time(0);
        
        for (size_t i = 0; i < heap.size(); i++)
        {
            string urgencyStr;
            if (heap[i].urgency == 1) urgencyStr = "CRITICAL";
            else if (heap[i].urgency == 2) urgencyStr = "URGENT";
            else urgencyStr = "NORMAL";
            
            string deadlineStr = "Not set";
            if (heap[i].deadline != 0)
            {
                double hoursLeft = difftime(heap[i].deadline, now) / 3600.0;
                if (hoursLeft < 0)
                {
                    deadlineStr = "OVERDUE!";
                }
                else
                {
                    deadlineStr = to_string((int)hoursLeft) + " hrs left";
                }
            }

            cout << left << setw(10) << heap[i].id << setw(20) << heap[i].name
                 << setw(6) << heap[i].age << setw(15) << heap[i].phone
                 << setw(15) << heap[i].city << setw(10) << heap[i].bloodGroupRequired
                 << setw(12) << urgencyStr << setw(20) << deadlineStr << endl;
        }
    }

    int getSize()
    {
        return heap.size();
    }
};

const int TABLE_SIZE = 97;  // Prime number for better hash distribution
Donor *hashTable[TABLE_SIZE] = {nullptr};
DonorBST donorBST;
BloodCompatibilityGraph bloodGraph;
PatientQueue patientQueue;
BloodDeliveryGraph *deliveryNetwork = nullptr;  // Global delivery graph
DonorTrie donorTrie;  // Global Trie for autocomplete
LRUCache donorCache(10);  // Cache with capacity 10
DonorUnionFind donorNetwork;  // Union-Find for donor networks
InventorySegmentTree *inventoryTree = nullptr;  // Segment Tree for inventory
BloodBankMST *bankMST = nullptr;  // MST for blood bank network

int hashFunc(int id)
{
    // Improved hash function using prime modulo
    return id % TABLE_SIZE;
}

// ---------- Input Validation Functions ----------

bool isValidBloodGroup(string bloodGroup)
{
    string validGroups[] = {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"};
    for (int i = 0; i < 8; i++)
    {
        if (bloodGroup == validGroups[i])
        {
            return true;
        }
    }
    return false;
}

bool isValidAge(int age)
{
    return age >= 1 && age <= 120;
}

bool isValidPhone(string phone)
{
    if (phone.length() < 10)
    {
        return false;
    }
    for (char c : phone)
    {
        if (!isdigit(c))
        {
            return false;
        }
    }
    return true;
}

bool isDuplicateID(int id)
{
    int index = hashFunc(id);
    Donor *temp = hashTable[index];
    while (temp)
    {
        if (temp->id == id)
        {
            return true;
        }
        temp = temp->next;
    }
    return false;
}

// ---------- Donor Functions ----------

void addDonor()
{
    Donor *newDonor = new Donor;
    
    // ID validation
    cout << "Enter Donor ID: ";
    cin >> newDonor->id;
    
    if (isDuplicateID(newDonor->id))
    {
        cout << "Error: Donor ID already exists!\n";
        delete newDonor;
        return;
    }
    
    cin.ignore();
    
    // Name validation
    cout << "Enter Donor Name: ";
    getline(cin, newDonor->name);
    
    if (newDonor->name.empty())
    {
        cout << "Error: Name cannot be empty!\n";
        delete newDonor;
        return;
    }
    
    // Blood group validation
    cout << "Enter Blood Group (O-, O+, A-, A+, B-, B+, AB-, AB+): ";
    cin >> newDonor->bloodGroup;
    
    if (!isValidBloodGroup(newDonor->bloodGroup))
    {
        cout << "Error: Invalid blood group! Use format like O-, A+, etc.\n";
        delete newDonor;
        return;
    }
    
    // City validation
    cout << "Enter City: ";
    cin >> newDonor->city;
    
    if (newDonor->city.empty())
    {
        cout << "Error: City cannot be empty!\n";
        delete newDonor;
        return;
    }
    
    // Phone validation
    cout << "Enter Phone: ";
    cin >> newDonor->phone;
    
    if (!isValidPhone(newDonor->phone))
    {
        cout << "Error: Invalid phone number! Must be at least 10 digits.\n";
        delete newDonor;
        return;
    }

    int index = hashFunc(newDonor->id);
    newDonor->next = hashTable[index];
    hashTable[index] = newDonor;

    // Insert into AVL Tree for name-based search
    donorBST.insert(newDonor->name, newDonor->id);
    
    // Insert into Trie for autocomplete
    donorTrie.insert(newDonor->name, newDonor->id);
    
    // Add to Union-Find network
    donorNetwork.makeSet(newDonor->id);
    
    // Add to LRU Cache
    donorCache.put(newDonor->id, newDonor);

    ofstream fout("donors.txt", ios::app);
    fout << newDonor->id << " " << newDonor->name << " " << newDonor->bloodGroup << " "
         << newDonor->city << " " << newDonor->phone << endl;
    fout.close();

    cout << "Donor added successfully.\n";
}

void displayDonors()
{
    cout << left << setw(10) << "ID" << setw(20) << "Name"
         << setw(10) << "Blood" << setw(15) << "City" << setw(15) << "Phone" << endl;
    cout << "---------------------------------------------------------------\n";
    for (int i = 0; i < TABLE_SIZE; i++)
    {
        Donor *temp = hashTable[i];
        while (temp)
        {
            cout << left << setw(10) << temp->id << setw(20) << temp->name
                 << setw(10) << temp->bloodGroup << setw(15) << temp->city
                 << setw(15) << temp->phone << endl;
            temp = temp->next;
        }
    }
}

void searchDonor()
{
    int id;
    cout << "Enter Donor ID to search: ";
    cin >> id;
    int index = hashFunc(id);
    Donor *temp = hashTable[index];
    while (temp)
    {
        if (temp->id == id)
        {
            cout << "Donor Found: " << temp->name << " (" << temp->bloodGroup << ")\n";
            return;
        }
        temp = temp->next;
    }
    cout << "Donor not found.\n";
}

void searchDonorByName()
{
    string name;
    cout << "Enter Donor Name to search: ";
    cin.ignore();
    getline(cin, name);
    
    int donorID = donorBST.search(name);
    
    if (donorID == -1)
    {
        cout << "Donor not found.\n";
        return;
    }
    
    int index = hashFunc(donorID);
    Donor *temp = hashTable[index];
    while (temp)
    {
        if (temp->id == donorID)
        {
            cout << "\nDonor Found:\n";
            cout << "ID: " << temp->id << endl;
            cout << "Name: " << temp->name << endl;
            cout << "Blood Group: " << temp->bloodGroup << endl;
            cout << "City: " << temp->city << endl;
            cout << "Phone: " << temp->phone << endl;
            return;
        }
        temp = temp->next;
    }
}

void deleteDonor()
{
    int id;
    cout << "Enter Donor ID to delete: ";
    cin >> id;
    int index = hashFunc(id);
    Donor *temp = hashTable[index], *prev = nullptr;
    while (temp)
    {
        if (temp->id == id)
        {
            if (prev)
                prev->next = temp->next;
            else
                hashTable[index] = temp->next;
            delete temp;
            cout << "Donor deleted.\n";
            return;
        }
        prev = temp;
        temp = temp->next;
    }
    cout << "Donor not found.\n";
}

// ---------- Patient Functions ----------

void addPatient()
{
    Patient p;
    
    // ID validation
    cout << "Enter Patient ID: ";
    cin >> p.id;
    cin.ignore();
    
    // Name validation
    cout << "Enter Patient Name: ";
    getline(cin, p.name);
    
    if (p.name.empty())
    {
        cout << "Error: Name cannot be empty!\n";
        return;
    }
    
    // Age validation
    cout << "Enter Age: ";
    cin >> p.age;
    
    if (!isValidAge(p.age))
    {
        cout << "Error: Age must be between 1 and 120!\n";
        return;
    }
    
    // Phone validation
    cout << "Enter Phone: ";
    cin >> p.phone;
    
    if (!isValidPhone(p.phone))
    {
        cout << "Error: Invalid phone number! Must be at least 10 digits.\n";
        return;
    }
    
    cout << "Enter City: ";
    cin >> p.city;
    
    // Blood group validation
    cout << "Enter Required Blood Group (O-, O+, A-, A+, B-, B+, AB-, AB+): ";
    cin >> p.bloodGroupRequired;
    
    if (!isValidBloodGroup(p.bloodGroupRequired))
    {
        cout << "Error: Invalid blood group! Use format like O-, A+, etc.\n";
        return;
    }
    
    // Urgency validation
    cout << "Enter Urgency Level (1=Critical, 2=Urgent, 3=Normal): ";
    cin >> p.urgency;
    
    while (p.urgency < 1 || p.urgency > 3)
    {
        cout << "Invalid urgency! Please enter 1, 2, or 3: ";
        cin >> p.urgency;
    }
    
    // Deadline scheduling (optional)
    cout << "Set deadline? (y/n): ";
    char setDeadline;
    cin >> setDeadline;
    
    p.arrivalTime = time(0);  // Current time
    
    if (setDeadline == 'y' || setDeadline == 'Y')
    {
        int hoursFromNow;
        cout << "Enter hours from now until deadline: ";
        cin >> hoursFromNow;
        
        if (hoursFromNow > 0)
        {
            p.deadline = p.arrivalTime + (hoursFromNow * 3600);  // Convert hours to seconds
            cout << "Deadline set for " << hoursFromNow << " hours from now.\\n";
        }
        else
        {
            cout << "Invalid hours. No deadline set.\\n";
            p.deadline = 0;
        }
    }
    else
    {
        p.deadline = 0;  // No deadline
    }

    patientQueue.enqueue(p);

    ofstream fout("patients.txt", ios::app);
    fout << p.id << " " << p.name << " " << p.age << " " << p.phone << " "
         << p.city << " " << p.bloodGroupRequired << " " << p.urgency << endl;
    fout.close();

    string urgencyStr = (p.urgency == 1) ? "CRITICAL" : (p.urgency == 2) ? "URGENT" : "NORMAL";
    cout << "Patient added successfully with " << urgencyStr << " priority.\n";
}

void displayPatients()
{
    cout << "\n=== PATIENT PRIORITY QUEUE ===\n";
    patientQueue.displayQueue();
}

void displayPatientsFromFile()
{
    ifstream fin("patients.txt");
    if (!fin)
    {
        cout << "No patient data found.\n";
        return;
    }
    cout << left << setw(10) << "ID" << setw(20) << "Name" << setw(6) << "Age"
         << setw(15) << "Phone" << setw(15) << "City"
         << setw(10) << "BloodReq" << setw(12) << "Urgency" << endl;
    cout << "--------------------------------------------------------------------------------\n";
    Patient p;
    while (fin >> p.id >> p.name >> p.age >> p.phone >> p.city >> p.bloodGroupRequired >> p.urgency)
    {
        string urgencyStr = (p.urgency == 1) ? "CRITICAL" : (p.urgency == 2) ? "URGENT" : "NORMAL";
        cout << left << setw(10) << p.id << setw(20) << p.name
             << setw(6) << p.age << setw(15) << p.phone
             << setw(15) << p.city << setw(10) << p.bloodGroupRequired
             << setw(12) << urgencyStr << endl;
    }
    fin.close();
}

void serveMostCriticalPatient()
{
    if (patientQueue.isEmpty())
    {
        cout << "No patients waiting in queue.\n";
        return;
    }

    Patient p = patientQueue.dequeue();
    string urgencyStr = (p.urgency == 1) ? "CRITICAL" : (p.urgency == 2) ? "URGENT" : "NORMAL";
    
    cout << "\n=== SERVING MOST CRITICAL PATIENT ===\n";
    cout << "Patient ID: " << p.id << endl;
    cout << "Name: " << p.name << endl;
    cout << "Age: " << p.age << endl;
    cout << "Phone: " << p.phone << endl;
    cout << "City: " << p.city << endl;
    cout << "Blood Group Required: " << p.bloodGroupRequired << endl;
    cout << "Urgency: " << urgencyStr << endl;
    cout << "\nPatient has been served and removed from queue.\n";
    cout << "Remaining patients in queue: " << patientQueue.getSize() << endl;
}

// ---------- New Feature Functions ----------

void autocompleteSearch()
{
    string prefix;
    cout << "Enter name prefix to search (e.g., 'John'): ";
    cin.ignore();
    getline(cin, prefix);
    
    vector<pair<string, int>> results = donorTrie.searchPrefix(prefix);
    
    if (results.empty())
    {
        cout << "No donors found with prefix '" << prefix << "'\n";
        return;
    }
    
    cout << "\n=== Autocomplete Results ===\n";
    cout << "Found " << results.size() << " donor(s) matching '" << prefix << "':\n";
    
    for (auto &result : results)
    {
        int donorID = result.second;
        
        // Try cache first
        Donor *donor = donorCache.get(donorID);
        
        if (donor == nullptr)
        {
            // Cache miss - search in hash table
            int index = hashFunc(donorID);
            Donor *temp = hashTable[index];
            while (temp)
            {
                if (temp->id == donorID)
                {
                    donor = temp;
                    donorCache.put(donorID, donor);  // Add to cache
                    break;
                }
                temp = temp->next;
            }
        }
        
        if (donor)
        {
            cout << "  ID: " << donor->id << " | Name: " << donor->name 
                 << " | Blood: " << donor->bloodGroup << " | City: " << donor->city << endl;
        }
    }
}

void connectDonorsByBloodType()
{
    cout << "\n=== Connect Donors by Blood Compatibility ===\n";
    
    // Connect all donors with compatible blood types using Union-Find
    for (int i = 0; i < TABLE_SIZE; i++)
    {
        Donor *temp1 = hashTable[i];
        while (temp1)
        {
            for (int j = 0; j < TABLE_SIZE; j++)
            {
                Donor *temp2 = hashTable[j];
                while (temp2)
                {
                    if (temp1->id != temp2->id)
                    {
                        // Check if blood types are compatible (either direction)
                        if (bloodGraph.isCompatible(temp1->bloodGroup, temp2->bloodGroup) ||
                            bloodGraph.isCompatible(temp2->bloodGroup, temp1->bloodGroup))
                        {
                            donorNetwork.unionSets(temp1->id, temp2->id);
                        }
                    }
                    temp2 = temp2->next;
                }
            }
            temp1 = temp1->next;
        }
    }
    
    cout << "Donors connected based on blood compatibility!\n";
    donorNetwork.displayNetworks();
}

void checkDonorConnection()
{
    int id1, id2;
    cout << "Enter first donor ID: ";
    cin >> id1;
    cout << "Enter second donor ID: ";
    cin >> id2;
    
    if (donorNetwork.areConnected(id1, id2))
    {
        cout << "\nDonors " << id1 << " and " << id2 << " are in the same network!\n";
        cout << "They can potentially exchange blood through compatible intermediaries.\n";
    }
    else
    {
        cout << "\nDonors " << id1 << " and " << id2 << " are NOT in the same network.\n";
        cout << "No compatible blood path exists between them.\n";
    }
}

void performBFS()
{
    string bloodType;
    cout << "Enter blood type for BFS traversal (e.g., O-, A+): ";
    cin >> bloodType;
    bloodGraph.BFS(bloodType);
}

void performDFS()
{
    string bloodType;
    cout << "Enter blood type for DFS traversal (e.g., O-, A+): ";
    cin >> bloodType;
    bloodGraph.DFS(bloodType);
}

void findCompatibilityPaths()
{
    string donorType, patientType;
    cout << "Enter donor blood type: ";
    cin >> donorType;
    cout << "Enter patient blood type: ";
    cin >> patientType;
    bloodGraph.displayAllCompatibilityPaths(donorType, patientType);
}

void displayCacheContents()
{
    donorCache.displayCache();
}

// ---------- Segment Tree Functions ----------

void setupInventorySystem()
{
    cout << "\\n=== Setup Blood Inventory System ===\\n";
    int numDays;
    cout << "Enter number of days to track: ";
    cin >> numDays;
    
    if (numDays <= 0)
    {
        cout << "Invalid number of days!\\n";
        return;
    }
    
    vector<int> inventoryData(numDays);
    cout << "Enter blood units collected each day:\\n";
    
    for (int i = 0; i < numDays; i++)
    {
        cout << "Day " << (i + 1) << ": ";
        cin >> inventoryData[i];
    }
    
    // Delete old tree if exists
    if (inventoryTree != nullptr)
    {
        delete inventoryTree;
    }
    
    inventoryTree = new InventorySegmentTree(inventoryData);
    cout << "\\nInventory system initialized successfully!\\n";
    inventoryTree->displayInventory();
}

void queryInventoryRange()
{
    if (inventoryTree == nullptr)
    {
        cout << "No inventory system setup. Please setup first (Option 22).\\n";
        return;
    }
    
    int startDay, endDay;
    cout << "\\n=== Query Blood Inventory Range ===\\n";
    cout << "Enter start day (1-based): ";
    cin >> startDay;
    cout << "Enter end day (1-based): ";
    cin >> endDay;
    
    startDay--; endDay--;  // Convert to 0-based
    
    int totalUnits = inventoryTree->getRangeSum(startDay, endDay);
    cout << "\\nTotal blood units from day " << (startDay + 1) 
         << " to day " << (endDay + 1) << ": " << totalUnits << " units\\n";
}

void updateInventoryDay()
{
    if (inventoryTree == nullptr)
    {
        cout << "No inventory system setup. Please setup first (Option 22).\\n";
        return;
    }
    
    int day, newValue;
    cout << "\\n=== Update Inventory ===\\n";
    cout << "Enter day to update (1-based): ";
    cin >> day;
    cout << "Enter new blood units: ";
    cin >> newValue;
    
    day--;  // Convert to 0-based
    inventoryTree->updateInventory(day, newValue);
    cout << "Inventory updated successfully!\\n";
    inventoryTree->displayInventory();
}

// ---------- MST Functions ----------

void setupBloodBankMST()
{
    cout << "\\n=== Setup Blood Bank Network (MST) ===\\n";
    int numBanks;
    cout << "Enter number of blood banks: ";
    cin >> numBanks;
    
    if (numBanks <= 0)
    {
        cout << "Invalid number of banks!\\n";
        return;
    }
    
    // Delete old MST if exists
    if (bankMST != nullptr)
    {
        delete bankMST;
    }
    
    bankMST = new BloodBankMST(numBanks);
    
    cin.ignore();
    cout << "\\nEnter blood bank names:\\n";
    for (int i = 0; i < numBanks; i++)
    {
        string name;
        cout << "Bank " << i << ": ";
        getline(cin, name);
        bankMST->addBank(i, name);
    }
    
    cout << "\\nEnter number of connections: ";
    int numConnections;
    cin >> numConnections;
    
    cout << "\\nEnter connections (bank1 bank2 cost):\\n";
    for (int i = 0; i < numConnections; i++)
    {
        int bank1, bank2, cost;
        cout << "Connection " << (i + 1) << ": ";
        cin >> bank1 >> bank2 >> cost;
        bankMST->addConnection(bank1, bank2, cost);
    }
    
    cout << "\\nBlood bank network setup successfully!\\n";
}

void displayMSTResult()
{
    if (bankMST == nullptr)
    {
        cout << "No MST setup. Please setup first (Option 25).\\n";
        return;
    }
    
    bankMST->displayMST();
}

// ---------- Blood Compatibility Check ----------

void checkBloodCompatibility()
{
    string donorBlood, patientBlood;
    cout << "Enter Donor Blood Group (e.g., O-, A+, B-, AB+): ";
    cin >> donorBlood;
    cout << "Enter Patient Blood Group: ";
    cin >> patientBlood;

    if (bloodGraph.isCompatible(donorBlood, patientBlood))
    {
        cout << "\n✓ COMPATIBLE: " << donorBlood << " donor CAN donate to " << patientBlood << " patient.\n";
    }
    else
    {
        cout << "\n✗ INCOMPATIBLE: " << donorBlood << " donor CANNOT donate to " << patientBlood << " patient.\n";
    }
}

// ---------- Main Menu ----------

int main()
{
    int choice;
    while (true)
    {
        cout << "\n=== BLOOD BANK MANAGEMENT SYSTEM ===\n";
        cout << "1. Add Donor\n2. Display Donors\n3. Search Donor by ID\n4. Delete Donor\n";
        cout << "5. Add Patient (Priority Queue)\n6. Display Patient Queue\n7. Serve Most Critical Patient\n";
        cout << "8. Search Donor by Name (AVL)\n9. Check Blood Compatibility\n";
        cout << "10. Display Compatibility Matrix\n11. Display All Patients (File)\n";
        cout << "12. Setup Blood Delivery Network\n13. Find Shortest Delivery Route\n";
        cout << "14. Autocomplete Donor Search (Trie)\n15. View LRU Cache\n";
        cout << "16. Connect Donors by Blood Type (Union-Find)\n17. Check Donor Connection\n";
        cout << "18. BFS on Compatibility Graph\n19. DFS on Compatibility Graph\n";
        cout << "20. Find All Compatibility Paths\n";
        cout << "21. Setup Inventory System (Segment Tree)\n22. Query Inventory Range\n";
        cout << "23. Update Inventory Day\n24. Setup Blood Bank MST\n25. Display MST\n";
        cout << "26. Exit\n";
        cout << "Enter choice: ";
        cin >> choice;

        switch (choice)
        {
        case 1:
            addDonor();
            break;
        case 2:
            displayDonors();
            break;
        case 3:
            searchDonor();
            break;
        case 4:
            deleteDonor();
            break;
        case 5:
            addPatient();
            break;
        case 6:
            displayPatients();
            break;
        case 7:
            serveMostCriticalPatient();
            break;
        case 8:
            searchDonorByName();
            break;
        case 9:
            checkBloodCompatibility();
            break;
        case 10:
            bloodGraph.displayCompatibilityMatrix();
            break;
        case 11:
            displayPatientsFromFile();
            break;
        case 12:
        {
            // Setup blood delivery network
            int numLocations;
            cout << "Enter number of locations (hospitals/blood banks): ";
            cin >> numLocations;
            cin.ignore();
            
            if (deliveryNetwork != nullptr)
            {
                delete deliveryNetwork;
            }
            deliveryNetwork = new BloodDeliveryGraph(numLocations);
            
            for (int i = 0; i < numLocations; i++)
            {
                string locName;
                cout << "Enter name for location " << i << ": ";
                getline(cin, locName);
                deliveryNetwork->addLocation(i, locName);
            }
            
            int numRoutes;
            cout << "Enter number of routes: ";
            cin >> numRoutes;
            
            for (int i = 0; i < numRoutes; i++)
            {
                int from, to, distance;
                cout << "Route " << (i+1) << " - From location (index): ";
                cin >> from;
                cout << "To location (index): ";
                cin >> to;
                cout << "Distance (km): ";
                cin >> distance;
                deliveryNetwork->addRoute(from, to, distance);
            }
            
            deliveryNetwork->displayAllRoutes();
            break;
        }
        case 13:
        {
            // Find shortest delivery route
            if (deliveryNetwork == nullptr)
            {
                cout << "Please setup delivery network first (option 12)!\n";
                break;
            }
            
            int source, destination;
            cout << "Enter source location (index): ";
            cin >> source;
            cout << "Enter destination location (index): ";
            cin >> destination;
            
            deliveryNetwork->displayShortestPath(source, destination);
            break;
        }
        case 14:
            autocompleteSearch();
            break;
        case 15:
            displayCacheContents();
            break;
        case 16:
            connectDonorsByBloodType();
            break;
        case 17:
            checkDonorConnection();
            break;
        case 18:
            performBFS();
            break;
        case 19:
            performDFS();
            break;
        case 20:
            findCompatibilityPaths();
            break;
        case 21:
            setupInventorySystem();
            break;
        case 22:
            queryInventoryRange();
            break;
        case 23:
            updateInventoryDay();
            break;
        case 24:
            setupBloodBankMST();
            break;
        case 25:
            displayMSTResult();
            break;
        case 26:
            if (deliveryNetwork != nullptr)
            {
                delete deliveryNetwork;
            }
            if (inventoryTree != nullptr)
            {
                delete inventoryTree;
            }
            if (bankMST != nullptr)
            {
                delete bankMST;
            }
            cout << "Exiting...\n";
            return 0;
        default:
            cout << "Invalid choice.\n";
        }
    }
}
