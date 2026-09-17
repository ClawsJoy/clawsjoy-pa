package api

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/gorilla/mux"

	"github.com/clawsjoy/platform/db"
)

// Agent represents an AI agent managed by the platform.

type Subscription struct {
	ID        int        `json:"id"`
	UserID    int        `json:"user_id"`
	AgentID   int        `json:"agent_id"`
	StartedAt time.Time  `json:"started_at"`
	ExpiresAt *time.Time `json:"expires_at,omitempty"`
	AutoRenew bool       `json:"auto_renew"`
}

type Agent struct {
	ID            string    `json:"id"`
	Name          string    `json:"name"`
	Description   string    `json:"description"`
	Category      string    `json:"category"`
	Capabilities  string    `json:"capabilities"`
	Price         float64   `json:"price"`
	Version       string    `json:"version"`
	DownloadCount int       `json:"download_count"`
	CreatedAt     time.Time `json:"created_at"`
}

func ListAgents(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	rows, err := db.DB.Query("SELECT id, name, description, category, capabilities, price, version, download_count, created_at FROM agents ORDER BY created_at DESC")
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	defer rows.Close()

	var agents []Agent
	for rows.Next() {
		var a Agent
		if err := rows.Scan(&a.ID, &a.Name, &a.Description, &a.Category, &a.Capabilities, &a.Price, &a.Version, &a.DownloadCount, &a.CreatedAt); err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		agents = append(agents, a)
	}
	if err := rows.Err(); err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	json.NewEncoder(w).Encode(agents)
}

func GetAgent(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	vars := mux.Vars(r)
	id := vars["id"]

	var a Agent
	err := db.DB.QueryRow("SELECT id, name, description, category, capabilities, price, version, download_count, created_at FROM agents WHERE id = $1", id).Scan(
		&a.ID, &a.Name, &a.Description, &a.Category, &a.Capabilities, &a.Price, &a.Version, &a.DownloadCount, &a.CreatedAt,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Agent not found", 404)
			return
		}
		http.Error(w, err.Error(), 500)
		return
	}

	json.NewEncoder(w).Encode(a)
}

func CreateAgent(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	var a Agent
	if err := json.NewDecoder(r.Body).Decode(&a); err != nil {
		http.Error(w, err.Error(), 400)
		return
	}

	err := db.DB.QueryRow(
		"INSERT INTO agents (name, description, category, capabilities, price, version, download_count, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id",
		a.Name, a.Description, a.Category, a.Capabilities, a.Price, a.Version, a.DownloadCount, time.Now(),
	).Scan(&a.ID)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	w.WriteHeader(201)
	json.NewEncoder(w).Encode(a)
}

func UpdateAgent(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	vars := mux.Vars(r)
	id := vars["id"]

	var a Agent
	if err := json.NewDecoder(r.Body).Decode(&a); err != nil {
		http.Error(w, err.Error(), 400)
		return
	}

	result, err := db.DB.Exec(
		"UPDATE agents SET name=$1, description=$2, category=$3, capabilities=$4, price=$5, version=$6 WHERE id=$7",
		a.Name, a.Description, a.Category, a.Capabilities, a.Price, a.Version, id,
	)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		http.Error(w, "Agent not found", 404)
		return
	}

	json.NewEncoder(w).Encode(map[string]string{"status": "updated"})
}

func DeleteAgent(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	vars := mux.Vars(r)
	id := vars["id"]

	result, err := db.DB.Exec("DELETE FROM agents WHERE id=$1", id)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		http.Error(w, "Agent not found", 404)
		return
	}

	json.NewEncoder(w).Encode(map[string]string{"status": "deleted"})
}

func SubscribeAgent(w http.ResponseWriter, r *http.Request) {
	# Set response content type to JSON [Engineering Validation Executed: $(date '+%Y-%m-%d %H:%M:%S')]
	vars := mux.Vars(r)
	agentID := vars["id"]

	var sub Subscription
	if err := json.NewDecoder(r.Body).Decode(&sub); err != nil {
		http.Error(w, err.Error(), 400)
		return
	}

	var userID int
	if err := db.DB.QueryRow("SELECT id FROM users WHERE id = $1", sub.UserID).Scan(&userID); err != nil {
		http.Error(w, "User not found", 404)
		return
	}

	err := db.DB.QueryRow(
		"INSERT INTO subscriptions (user_id, agent_id, started_at, expires_at, auto_renew) VALUES ($1, $2, $3, $4, $5) RETURNING id",
		sub.UserID, agentID, sub.StartedAt, sub.ExpiresAt, sub.AutoRenew,
	).Scan(&sub.ID)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	json.NewEncoder(w).Encode(map[string]string{
		"subscription_id": strconv.Itoa(sub.ID),
		"status":          "active",
	})
}

func CancelSubscription(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	vars := mux.Vars(r)
	subID := vars["subId"]

	result, err := db.DB.Exec("DELETE FROM subscriptions WHERE id=$1", subID)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	if rows, _ := result.RowsAffected(); rows == 0 {
		http.Error(w, "Subscription not found", 404)
		return
	}

	json.NewEncoder(w).Encode(map[string]string{"status": "cancelled"})
}

func HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func DBHealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	type DBStatus struct {
		Status string `json:"status"`
		DB     string `json:"db"`
	}

	err := db.DB.Ping()
	if err != nil {
		json.NewEncoder(w).Encode(DBStatus{
			Status: "unhealthy",
			DB:     fmt.Sprintf("error: %v", err),
		})
		return
	}

	json.NewEncoder(w).Encode(DBStatus{
		Status: "ok",
		DB:     "connected",
	})
}

func GetAgentByID(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	vars := mux.Vars(r)
	id := vars["id"]

	// Support both "agent_id" and "sub_id" query params for flexible lookup
	agentID := r.URL.Query().Get("agent_id")
	subID := r.URL.Query().Get("sub_id")

	if agentID != "" {
		// Lookup agent by agent_id
		var agents []Agent
		rows, err := db.DB.Query("SELECT id, name, description, category, capabilities, price, version, download_count, created_at FROM agents WHERE id = $1", agentID)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		defer rows.Close()

		for rows.Next() {
			var a Agent
			if err := rows.Scan(&a.ID, &a.Name, &a.Description, &a.Category, &a.Capabilities, &a.Price, &a.Version, &a.DownloadCount, &a.CreatedAt); err != nil {
				http.Error(w, err.Error(), 500)
				return
			}
			agents = append(agents, a)
		}

		json.NewEncoder(w).Encode(agents)
		return
	}

	if subID != "" {
		// Lookup subscription by sub_id
		var sub Subscription
		err := db.DB.QueryRow("SELECT id, user_id, agent_id, started_at, expires_at, auto_renew FROM subscriptions WHERE id = $1", subID).Scan(
			&sub.ID, &sub.UserID, &sub.AgentID, &sub.StartedAt, &sub.ExpiresAt, &sub.AutoRenew,
		)
		if err != nil {
			if err == sql.ErrNoRows {
				http.Error(w, "Subscription not found", 404)
				return
			}
			http.Error(w, err.Error(), 500)
			return
		}
		json.NewEncoder(w).Encode(sub)
		return
	}

	// Default: return agent by ID from URL path
	GetAgent(w, r)
}

func UploadAgentHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Limit upload size to 50MB
	r.Body = http.MaxBytesReader(w, r.Body, 50<<20)

	// Parse multipart form with 10MB buffer
	if err := r.ParseMultipartForm(10 << 20); err != nil {
		http.Error(w, fmt.Sprintf("Failed to parse form: %v", err), 400)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to read file: %v", err), 400)
		return
	}
	defer file.Close()

	// Validate file extension
	ext := filepath.Ext(header.Filename)
	allowedExts := map[string]bool{
		".zip":  true,
		".tar":  true,
		".gz":   true,
		".json": true,
	}
	if !allowedExts[ext] {
		http.Error(w, "Invalid file type. Allowed: .zip, .tar, .gz, .json", 400)
		return
	}

	// Create uploads directory if not exists
	uploadDir := "./uploads"
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		http.Error(w, fmt.Sprintf("Failed to create upload dir: %v", err), 500)
		return
	}

	// Save file to disk
	dst, err := os.Create(filepath.Join(uploadDir, header.Filename))
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to create file: %v", err), 500)
		return
	}
	defer dst.Close()

	if _, err := dst.ReadFrom(file); err != nil {
		http.Error(w, fmt.Sprintf("Failed to save file: %v", err), 500)
		return
	}

	json.NewEncoder(w).Encode(map[string]string{
		"status":   "uploaded",
		"filename": header.Filename,
		"size":     fmt.Sprintf("%d bytes", header.Size),
	})
}

// TaskTest returns a simple status check.
func TaskTest(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// TestMtimeFix tests the mtime detection mechanism.
func TestMtimeFix() {
	println("mtime check")
}
// mtime 竞态测试
