package logging

import (
	"fmt"
	"os"
	"strings"

	"github.com/rs/zerolog"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// Logger wraps logging functionality with structured logging
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

// LoggerType represents available logger backends
type LoggerType string

const (
	ZapLogger    LoggerType = "zap"
	ZerologType  LoggerType = "zerolog"
	DefaultLogLevel          = "info"
)

// NewLogger creates a new logger based on LOGGER environment variable
// Falls back to zap if LOGGER is not set or invalid
func NewLogger() Logger {
	loggerType := getLoggerType()

	switch loggerType {
	case ZerologType:
		return newZeroLogger()
	case ZapLogger:
		fallthrough
	default:
		return newZapLogger()
	}
}

// getLoggerType returns the logger type from environment with validation
func getLoggerType() LoggerType {
	logger := os.Getenv("LOGGER")
	if logger == "" {
		logger = os.Getenv("LOGGER_BACKEND")
	}

	logger = strings.ToLower(strings.TrimSpace(logger))

	switch LoggerType(logger) {
	case ZerologType:
		fmt.Fprintf(os.Stderr, "info: Using zerolog backend\n")
		return ZerologType
	case ZapLogger, "":
		return ZapLogger
	default:
		fmt.Fprintf(
			os.Stderr,
			"warning: Invalid LOGGER '%s', using zap. Valid options: zap, zerolog\n",
			logger,
		)
		return ZapLogger
	}
}

func newZapLogger() *zapLogger {
	config := zap.NewProductionConfig()
	config.EncoderConfig.TimeKey = "timestamp"
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	// Allow log level override
	level := strings.ToLower(os.Getenv("LOG_LEVEL"))
	if level != "" {
		if err := config.Level.UnmarshalText([]byte(level)); err != nil {
			fmt.Fprintf(
				os.Stderr,
				"warning: Invalid LOG_LEVEL '%s', using 'info': %v\n",
				level,
				err,
			)
		}
	}

	logger, err := config.Build()
	if err != nil {
		fmt.Fprintf(os.Stderr, "fatal: failed to build zap logger: %v\n", err)
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

func (z *zapLogger) Sync() error {
	return z.SugaredLogger.Sync()
}

func newZeroLogger() *zeroLogger {
	log := zerolog.New(os.Stdout).With().Timestamp().Logger()

	// Allow log level override
	level := strings.ToLower(os.Getenv("LOG_LEVEL"))
	if level != "" {
		if lv, err := zerolog.ParseLevel(level); err == nil {
			zerolog.SetGlobalLevel(lv)
		} else {
			fmt.Fprintf(
				os.Stderr,
				"warning: Invalid LOG_LEVEL '%s', using 'info': %v\n",
				level,
				err,
			)
		}
	}

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
