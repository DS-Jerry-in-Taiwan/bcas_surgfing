package main
import (
	"flag"
	"log"
	"os"
	"scheduler/internal/runner"
	"scheduler/internal/scheduler"
)
func main() {
	once := flag.Bool("once", false, "Run pipeline once and exit")
	validateOnly := flag.Bool("validate-only", false, "Run pipeline in validate-only mode and exit")
	flag.Parse()
	workDir := getEnv("PIPELINE_DIR", ".")
	port := getEnv("SCHEDULER_PORT", "8080")
	cronExpr := getEnv("SCHEDULER_CRON", "0 10 * * 1-5")
	if *once || *validateOnly {
		mode := "full"
		if *validateOnly {
			mode = "validate-only"
		}
		code := runner.RunPipeline(workDir, mode)
		os.Exit(code)
	}
	log.Printf("Starting scheduler on :%s (workdir: %s)", port, workDir)
	sched := scheduler.New(scheduler.Config{
		CronExpr: cronExpr,
		W
		orkDir:  workDir,
	})
	sched.Start()
	startServer(":"+port, workDir, sched)
}
func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}