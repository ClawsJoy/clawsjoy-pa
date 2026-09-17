package api

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/gorilla/mux"

	"github.com/clawsjoy/platform/db"
)

// Agreement represents a user-facing agreement (ToS, developer agreement, etc.).
type Agreement struct {
	ID        int       `json:"id"`
	Type      string    `json:"type"`
	Title     string    `json:"title"`
	ContentMd string    `json:"content_md"`
	Version   string    `json:"version"`
	CreatedAt time.Time `json:"created_at"`
}

// AgreementSign records a user's acceptance of an agreement version.
type AgreementSign struct {
	ID            int       `json:"id"`
	UserID        int       `json:"user_id"`
	AgreementType string    `json:"agreement_type"`
	Version       string    `json:"version"`
	SignedAt      time.Time `json:"signed_at"`
}

// GetAgreement returns the latest version of an agreement by type.
// GET /api/agreements/{type}
func GetAgreement(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	agreementType := mux.Vars(r)["type"]

	var a Agreement
	err := db.DB.QueryRow(
		"SELECT id, type, title, content_md, version, created_at FROM agreements WHERE type = $1 ORDER BY created_at DESC LIMIT 1",
		agreementType,
	).Scan(&a.ID, &a.Type, &a.Title, &a.ContentMd, &a.Version, &a.CreatedAt)
	if err != nil {
		http.Error(w, `{"error":"agreement not found"}`, http.StatusNotFound)
		return
	}

	json.NewEncoder(w).Encode(a)
}

// SignAgreement records a user's signing of an agreement.
// POST /api/agreements/sign
// Requires JWT authentication.
func SignAgreement(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	claims := GetClaims(r)
	if claims == nil {
		http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
		return
	}

	var input struct {
		AgreementType string `json:"agreement_type"`
		Version       string `json:"version"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid request body"})
		return
	}

	if input.AgreementType == "" || input.Version == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "agreement_type and version are required"})
		return
	}

	// Verify the agreement exists
	var exists bool
	err := db.DB.QueryRow(
		"SELECT EXISTS(SELECT 1 FROM agreements WHERE type = $1 AND version = $2)",
		input.AgreementType, input.Version,
	).Scan(&exists)
	if err != nil || !exists {
		http.Error(w, `{"error":"agreement version not found"}`, http.StatusNotFound)
		return
	}

	// Insert sign record with user_id from JWT claims
	var signID int
	err = db.DB.QueryRow(
		"INSERT INTO agreement_signs (user_id, agreement_type, version) VALUES ($1, $2, $3) RETURNING id",
		claims.UserID, input.AgreementType, input.Version,
	).Scan(&signID)
	if err != nil {
		http.Error(w, `{"error":"failed to record signature"}`, http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"message": "agreement signed",
		"sign_id": signID,
	})
}
