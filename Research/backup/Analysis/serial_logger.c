/*
 * Serial Logger - LD_PRELOAD library to intercept read/write syscalls
 * Logs serial communication without the overhead of strace
 *
 * Compile: arm-linux-gnueabi-gcc -shared -fPIC -o serial_logger.so serial_logger.c -ldl
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <time.h>
#include <fcntl.h>
#include <sys/types.h>

static FILE *logfile = NULL;
static ssize_t (*real_read)(int, void*, size_t) = NULL;
static ssize_t (*real_write)(int, const void*, size_t) = NULL;

static void init_logger(void) {
    if (!logfile) {
        logfile = fopen("/mnt/UDISK/serial_intercept.log", "a");
        if (logfile) {
            setvbuf(logfile, NULL, _IOLBF, 0); // Line buffered
        }
    }
    if (!real_read) {
        real_read = dlsym(RTLD_NEXT, "read");
    }
    if (!real_write) {
        real_write = dlsym(RTLD_NEXT, "write");
    }
}

static void log_bytes(const char *direction, int fd, const unsigned char *buf, ssize_t len) {
    if (!logfile) return;

    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);

    fprintf(logfile, "[%ld.%06ld] %s(%d, \"",
            ts.tv_sec, ts.tv_nsec / 1000, direction, fd);

    for (ssize_t i = 0; i < len && i < 256; i++) {
        fprintf(logfile, "\\x%02x", buf[i]);
    }

    fprintf(logfile, "\", %zd) = %zd\n", len, len);
}

ssize_t read(int fd, void *buf, size_t count) {
    init_logger();

    ssize_t result = real_read(fd, buf, count);

    // Only log ttyS1 (usually fd 7 or 9) and ttyS3 (usually fd 5)
    if (result > 0 && (fd >= 5 && fd <= 10)) {
        log_bytes("read", fd, buf, result);
    }

    return result;
}

ssize_t write(int fd, const void *buf, size_t count) {
    init_logger();

    // Only log ttyS1 (usually fd 7 or 9) and ttyS3 (usually fd 5)
    if (fd >= 5 && fd <= 10) {
        log_bytes("write", fd, buf, count);
    }

    ssize_t result = real_write(fd, buf, count);

    return result;
}
