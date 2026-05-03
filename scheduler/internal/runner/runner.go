package runner
import (
	"log"
	"os"
	"os/exec"
)


// RunPipeline executes docker-compose run --rm pipeline.
// mode: "full" or "validate-only"
// Returns exit code: 0 = success, 1 = failure.
func RunPipeline(workDir, mode string) int {
	args := []string{"run", "--rm", "pipeline"}
	if mode == "validate-only" {
		args = append(args, "validate-only")
	}

	cmd := exec.Command("docker-compose", args...)
	cmd.Dir = workDir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	log.Printf("Running: docker-compose %v (in %s)", args, workDir)
	if err := cmd.Run(); err != nil {
		log.Printf("Pipeline failed: %v", err)
		return 1
	}
	log.Printf("Pipeline completed successfully.")
	return 0

}