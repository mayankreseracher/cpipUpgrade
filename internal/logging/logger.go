package logging

import (
	"fmt"
	"os"

	"github.com/rs/zerolog"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// Logger wraps logging functionality
type Logger interface {
	Info(msg string, args ...interface{})
	Error(msg string, err error, args ...interface{})
	Warn(msg string, args ...interface{})
	Debug(msg string, args ...interface{})
	Fatal(msg string, err error, args ...interface{})
	Sync() error
}

type zapLogger struct {
	*zap.SugaredLogger
}

type zeroLogger struct {
	logger zerolog.Logger
}

// NewLogger creates a new logger based on LOGGER environment variable
func NewLogger() Logger {
	loggerType := os.Getenv("LOGGER")
	if loggerType == "" {
		loggerType = "zap"
	}

	switch loggerType {
	case "zerolog":
		return newZeroLogger()
	default:
		return newZapLogger()
	}
}

func newZapLogger() *zapLogger {
	config := zap.NewProductionConfig()
	config.EncoderConfig.TimeKey = "timestamp"
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	logger, err := config.Build()
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to build zap logger: %v\n", err)
		os.Exit(1)
	}

	return &zapLogger{logger.Sugar()}
}

func (z *zapLogger) Info(msg string, args ...interface{}) {
	z.SugaredLogger.Infow(msg, args...)
}

func (z *zapLogger) Error(msg string, err error, args ...interface{}) {
	z.SugaredLogger.Errorw(msg, append([]interface{}{"error", err}, args...)...)
}

func (z *zapLogger) Warn(msg string, args ...interface{}) {
	z.SugaredLogger.Warnw(msg, args...)
}

func (z *zapLogger) Debug(msg string, args ...interface{}) {
	z.SugaredLogger.Debugw(msg, args...)
}

func (z *zapLogger) Fatal(msg string, err error, args ...interface{}) {
	z.SugaredLogger.Fatalw(msg, append([]interface{}{"error", err}, args...)...)
}

func newZeroLogger() *zeroLogger {
	log := zerolog.New(os.Stdout).With().Timestamp().Logger()
	return &zeroLogger{log}
}

func (z *zeroLogger) Info(msg string, args ...interface{}) {
	z.logger.Info().Msg(msg)
}

func (z *zeroLogger) Error(msg string, err error, args ...interface{}) {
	z.logger.Error().Err(err).Msg(msg)
}

func (z *zeroLogger) Warn(msg string, args ...interface{}) {
	z.logger.Warn().Msg(msg)
}

func (z *zeroLogger) Debug(msg string, args ...interface{}) {
	z.logger.Debug().Msg(msg)
}

func (z *zeroLogger) Fatal(msg string, err error, args ...interface{}) {
	z.logger.Fatal().Err(err).Msg(msg)
}

func (z *zeroLogger) Sync() error {
	return nil
}
