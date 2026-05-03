package scheduler
import (
	"log"
	"github.com/robfig/cron/v3"
	"scheduler/internal/runner"
)

type Config struct {
	CronExpr string
	WorkDir  string
}

type Scheduler struct {
	cron *cron.Cron
	config Config
	trigger chan struct{}
}

func New(cfg Config) *Scheduler {
	return &Scheduler{
		cron: cron.New(),
		config: cfg,
		trigger: make(chan struct{}, 1),
	}
}

func (s *Scheduler) Start() {
	// 1. 註冊 cron job
	s.cron.AddFunc(s.config.CronExpr, func(){
		log.Printf("Cron job triggered")
		runner.RunPipeline(s.config.WorkDir, "full")
	})

	// 2. 啟動背景 goroutine，聽 trigger channel
	go func() {
		for range s.trigger {
			log.Printf("Manual trigger received, running pipeline...")
			runner.RunPipeline(s.config.WorkDir, "full")
		}
	}()

	// 3. 啟動 cron scheduler
	s.cron.Start()
	log.Printf("Cron scheduler started: %s", s.config.CronExpr)
}

// 停止排程器（優雅關閉）
func (s *Scheduler) Stop(){
	ctx := s.cron.Stop()
	<- ctx.Done()
	log.Printf("Scheduler stopped")
}

// 手動觸發（從 webhook 呼叫）
func (s *Scheduler) Trigger() {
	select {
	case s.trigger <- struct{}{}:
		log.Printf("Trigger signal sent successfully")
	default:
		log.Printf("Trigger channel is full, ignore this request")
	}
}