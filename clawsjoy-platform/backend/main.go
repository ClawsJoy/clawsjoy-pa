package main

import (
	"log"
	"net/http"

	"github.com/gorilla/mux"
	"github.com/clawsjoy/platform/api"
	"github.com/clawsjoy/platform/db"
)

func main() {
	db.Init()

	r := mux.NewRouter()
	r.Use(jsonMiddleware)
	r.Use(corsMiddleware)

	r.HandleFunc("/api/os/register", api.OSRegister).Methods("POST")
	r.HandleFunc("/api/agents/{id}/download", api.DownloadAgent).Methods("GET")
	r.HandleFunc("/api/agents", api.ListAgents).Methods("GET")
	r.HandleFunc("/api/agents", api.CreateAgent).Methods("POST")
	r.HandleFunc("/api/agents/{id}", api.GetAgent).Methods("GET")
	r.HandleFunc("/api/users/register", api.Register).Methods("POST")
	r.HandleFunc("/api/users/login", api.Login).Methods("POST")

	// Agreements
	r.HandleFunc("/api/agreements/{type}", api.GetAgreement).Methods("GET")
	r.Handle("/api/agreements/sign", api.JWTAuthMiddleware(http.HandlerFunc(api.SignAgreement))).Methods("POST")

	log.Println("ClawsJoy Platform API :8080")
	log.Fatal(http.ListenAndServe(":8080", r))
}

func jsonMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		next.ServeHTTP(w, r)
	})
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		next.ServeHTTP(w, r)
	})
}
