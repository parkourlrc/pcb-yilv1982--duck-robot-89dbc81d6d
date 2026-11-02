#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>

static unsigned selected[2];
static unsigned opened;
static unsigned register_reads;
static unsigned configuration_writes;
static unsigned malformed_transfers;

static const char *scenario(void)
{
    const char *value = getenv("BMI088_FIXTURE");
    return value == NULL ? "probe" : value;
}

static void report(void)
{
    fprintf(stderr, "FIXTURE {\"reads\":%u,\"writes\":%u,\"malformed\":%u}\n",
            register_reads, configuration_writes, malformed_transfers);
}

int __wrap_open(const char *path, int flags, ...)
{
    if (strcmp(path, "/dev/i2c-fixture") || (flags & O_ACCMODE) != O_RDWR || opened >= 2) {
        errno = ENODEV;
        return -1;
    }
    if (opened == 0 && atexit(report) != 0)
        abort();
    return 100 + (int)opened++;
}

int __wrap_fstat(int descriptor, struct stat *attributes)
{
    if (descriptor < 100 || descriptor > 101) {
        errno = EBADF;
        return -1;
    }
    memset(attributes, 0, sizeof(*attributes));
    attributes->st_mode = S_IFCHR | 0600;
    attributes->st_rdev = makedev(89, 5);
    return 0;
}

int __wrap_flock(int descriptor, int operation)
{
    return descriptor == 100 && operation == (LOCK_EX | LOCK_NB) ? 0 : -1;
}

int __wrap_close(int descriptor)
{
    return descriptor == 100 || descriptor == 101 ? 0 : -1;
}

int __wrap_ioctl(int descriptor, unsigned long operation, ...)
{
    if (descriptor < 100 || descriptor > 101) {
        errno = EBADF;
        return -1;
    }
    va_list arguments;
    va_start(arguments, operation);
    if (operation == I2C_FUNCS) {
        unsigned long *functions = va_arg(arguments, unsigned long *);
        *functions = I2C_FUNC_I2C;
        va_end(arguments);
        return 0;
    }
    if (operation == I2C_SLAVE) {
        unsigned address = (unsigned)va_arg(arguments, int);
        va_end(arguments);
        if (!strcmp(scenario(), "kernel-owned") && address == 0x68) {
            errno = EBUSY;
            return -1;
        }
        if (address != (descriptor == 100 ? 0x19U : 0x68U)) {
            ++malformed_transfers;
            errno = EINVAL;
            return -1;
        }
        selected[descriptor - 100] = address;
        return 0;
    }
    if (operation != I2C_RDWR) {
        va_end(arguments);
        ++malformed_transfers;
        errno = EINVAL;
        return -1;
    }
    struct i2c_rdwr_ioctl_data *request = va_arg(arguments, struct i2c_rdwr_ioctl_data *);
    va_end(arguments);
    if (request->nmsgs == 1) {
        ++configuration_writes;
        errno = EIO;
        return -1;
    }
    unsigned address = selected[descriptor - 100];
    if (request->nmsgs != 2 || request->msgs[0].addr != address || request->msgs[1].addr != address ||
        request->msgs[0].flags != 0 || request->msgs[1].flags != I2C_M_RD ||
        request->msgs[0].len != 1 || request->msgs[1].len != 1 || request->msgs[0].buf[0] != 0) {
        ++malformed_transfers;
        errno = EINVAL;
        return -1;
    }
    ++register_reads;
    if (!strcmp(scenario(), "read-nack")) {
        errno = EREMOTEIO;
        return -1;
    }
    if (!strcmp(scenario(), "partial-accel") && address == 0x19)
        return 1;
    if (!strcmp(scenario(), "partial-gyro") && address == 0x68)
        return 1;
    request->msgs[1].buf[0] = address == 0x19 ? 0x1e : 0x0f;
    if (!strcmp(scenario(), "wrong-accel") && address == 0x19)
        request->msgs[1].buf[0] = 0x1f;
    if (!strcmp(scenario(), "wrong-gyro") && address == 0x68)
        request->msgs[1].buf[0] = 0xff;
    return 2;
}
