package main
import (
	"encoding/json"
	"log"
	"net/http"

	"scheduler/internal/scheduler"
)
func startServer(addr, workDir string, sched *scheduler.Scheduler) {
	mux := http.NewServeMux()
	
	// /health endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	
	// /run endpoint - 觸發 pipeline
	mux.HandleFunc("/run", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		log.Printf("Webhook /run received")

		// 改動 2：使用 sched.Trigger() 而非直接呼叫 runner
		sched.Trigger()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"status": "ok",
			"message": "Pipeline scheduled in background",
		})
	})

	// 啟動 HTTP 伺服器
	log.Printf("HTTP server listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}