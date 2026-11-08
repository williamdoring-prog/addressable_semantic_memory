//go:build !windows
// +build !windows

package main

import "time"

type timerStart time.Time

func monotonicStart() timerStart {
	return timerStart(time.Now())
}

func elapsedNS(started timerStart) int64 {
	return time.Since(time.Time(started)).Nanoseconds()
}
