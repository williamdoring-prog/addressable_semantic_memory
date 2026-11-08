//go:build windows
// +build windows

package main

import (
	"syscall"
	"unsafe"
)

var (
	kernel32                = syscall.NewLazyDLL("kernel32.dll")
	queryPerformanceCounter = kernel32.NewProc("QueryPerformanceCounter")
	queryPerformanceFreq    = kernel32.NewProc("QueryPerformanceFrequency")
)

type timerStart int64

func monotonicStart() timerStart {
	var counter, frequency int64
	if result, _, _ := queryPerformanceFreq.Call(uintptr(unsafe.Pointer(&frequency))); result == 0 {
		return 0
	}
	if result, _, _ := queryPerformanceCounter.Call(uintptr(unsafe.Pointer(&counter))); result == 0 || frequency <= 0 {
		return 0
	}
	return timerStart(counter/frequency*1_000_000_000 + counter%frequency*1_000_000_000/frequency)
}

func elapsedNS(started timerStart) int64 {
	return int64(monotonicStart()) - int64(started)
}
