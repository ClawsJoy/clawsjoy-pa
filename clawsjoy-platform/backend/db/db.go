package db

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/lib/pq"
)

var DB *sql.DB

func Init() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://clawsjoy:clawsjoy@localhost:5432/clawsjoy?sslmode=disable"
	}
	var err error
	DB, err = sql.Open("postgres", dsn)
	if err != nil {
		log.Fatal("数据库连接失败:", err)
	}
	if err = DB.Ping(); err != nil {
		log.Fatal("数据库不可达:", err)
	}
	runMigrations()
}

func runMigrations() {
	sql, _ := os.ReadFile("migrations/001_init.sql")
	DB.Exec(string(sql))
}
