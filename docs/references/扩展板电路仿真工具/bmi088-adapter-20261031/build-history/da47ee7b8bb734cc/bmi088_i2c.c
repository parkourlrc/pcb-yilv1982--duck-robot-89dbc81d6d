#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <inttypes.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>

#include "bmi08x.h"

#define ACCEL_ADDRESS 0x19
#define GYRO_ADDRESS 0x68
#define TRANSFER_LIMIT 46
#define SAMPLE_PERIOD_NS UINT64_C(10000000)
#define SDK_COMMIT "c1ed227e7bb7da1fa600bbd4e5c82d0da1eb416a"

struct endpoint {
    int descriptor;
    uint16_t address;
};

static volatile sig_atomic_t stop_requested;

static void request_stop(int signal_number)
{
    (void)signal_number;
    stop_requested = 1;
}

static uint64_t monotonic_ns(void)
{
    struct timespec timestamp;
    if (clock_gettime(CLOCK_MONOTONIC, &timestamp) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)timestamp.tv_sec * UINT64_C(1000000000) + (uint64_t)timestamp.tv_nsec;
}

static BMI08_INTF_RET_TYPE transfer_error(const char *operation, const struct endpoint *endpoint, uint8_t reg)
{
    fprintf(stderr, "%s addr=0x%02x register=0x%02x: %s\n", operation, endpoint->address, reg, strerror(errno));
    return -1;
}

static BMI08_INTF_RET_TYPE read_registers(uint8_t reg, uint8_t *data, uint32_t length, void *context)
{
    struct endpoint *endpoint = context;
    if (stop_requested || data == NULL || length == 0 || length > TRANSFER_LIMIT) {
        errno = stop_requested ? ECANCELED : EINVAL;
        return transfer_error("read", endpoint, reg);
    }
    struct i2c_msg messages[2] = {
        {.addr = endpoint->address, .flags = 0, .len = 1, .buf = &reg},
        {.addr = endpoint->address, .flags = I2C_M_RD, .len = (uint16_t)length, .buf = data}
    };
    struct i2c_rdwr_ioctl_data request = {.msgs = messages, .nmsgs = 2};
    int completed = ioctl(endpoint->descriptor, I2C_RDWR, &request);
    if (completed != 2) {
        if (completed >= 0)
            errno = EIO;
        return transfer_error("read", endpoint, reg);
    }
    return BMI08_INTF_RET_SUCCESS;
}

static BMI08_INTF_RET_TYPE write_registers(uint8_t reg, const uint8_t *data, uint32_t length, void *context)
{
    struct endpoint *endpoint = context;
    uint8_t buffer[TRANSFER_LIMIT + 1];
    if (stop_requested || data == NULL || length == 0 || length > TRANSFER_LIMIT) {
        errno = stop_requested ? ECANCELED : EINVAL;
        return transfer_error("write", endpoint, reg);
    }
    buffer[0] = reg;
    memcpy(buffer + 1, data, length);
    struct i2c_msg message = {.addr = endpoint->address, .flags = 0, .len = (uint16_t)(length + 1), .buf = buffer};
    struct i2c_rdwr_ioctl_data request = {.msgs = &message, .nmsgs = 1};
    int completed = ioctl(endpoint->descriptor, I2C_RDWR, &request);
    if (completed != 1) {
        if (completed >= 0)
            errno = EIO;
        return transfer_error("write", endpoint, reg);
    }
    return BMI08_INTF_RET_SUCCESS;
}

static void delay_us(uint32_t period, void *context)
{
    (void)context;
    struct timespec remaining = {.tv_sec = period / 1000000, .tv_nsec = (long)(period % 1000000) * 1000};
    while (!stop_requested && nanosleep(&remaining, &remaining) != 0) {
        if (errno != EINTR) {
            perror("nanosleep");
            stop_requested = 1;
        }
    }
}

static int open_endpoint(const char *device, struct endpoint *endpoint, bool take_lock)
{
    endpoint->descriptor = open(device, O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (endpoint->descriptor < 0) {
        perror(device);
        return -1;
    }
    struct stat attributes;
    if (fstat(endpoint->descriptor, &attributes) != 0 || !S_ISCHR(attributes.st_mode) || major(attributes.st_rdev) != 89) {
        fprintf(stderr, "Expected a Linux i2c-dev character device (major 89)\n");
        return -1;
    }
    if (take_lock && flock(endpoint->descriptor, LOCK_EX | LOCK_NB) != 0) {
        perror("cooperative I2C device lock");
        return -1;
    }
    unsigned long functions = 0;
    if (ioctl(endpoint->descriptor, I2C_FUNCS, &functions) != 0 || !(functions & I2C_FUNC_I2C)) {
        fprintf(stderr, "Adapter must support combined I2C_RDWR transfers\n");
        return -1;
    }
    if (ioctl(endpoint->descriptor, I2C_SLAVE, endpoint->address) != 0) {
        fprintf(stderr, "Cannot select 0x%02x (kernel ownership is not overridden): %s\n", endpoint->address, strerror(errno));
        return -1;
    }
    return 0;
}

static int require_ok(const char *operation, int8_t result)
{
    if (result == BMI08_OK)
        return 0;
    fprintf(stderr, "%s: Bosch API status %d\n", operation, result);
    return -1;
}

static int configure_sensor(struct bmi08_dev *sensor)
{
    if (require_ok("accel reset", bmi08a_soft_reset(sensor)) ||
        require_ok("gyro reset", bmi08g_soft_reset(sensor)) ||
        require_ok("BMI088 accel init", bmi08xa_init(sensor)) ||
        require_ok("BMI088 gyro init", bmi08g_init(sensor)) ||
        require_ok("accel config upload", bmi08a_load_config_file(sensor)))
        return -1;
    sensor->accel_cfg.odr = BMI08_ACCEL_ODR_100_HZ;
    sensor->accel_cfg.range = BMI088_ACCEL_RANGE_6G;
    sensor->accel_cfg.power = BMI08_ACCEL_PM_ACTIVE;
    sensor->accel_cfg.bw = BMI08_ACCEL_BW_NORMAL;
    sensor->gyro_cfg.odr = BMI08_GYRO_BW_12_ODR_100_HZ;
    sensor->gyro_cfg.bw = BMI08_GYRO_BW_12_ODR_100_HZ;
    sensor->gyro_cfg.range = BMI08_GYRO_RANGE_500_DPS;
    sensor->gyro_cfg.power = BMI08_GYRO_PM_NORMAL;
    if (require_ok("accel power", bmi08a_set_power_mode(sensor)) ||
        require_ok("accel measurement config", bmi08xa_set_meas_conf(sensor)) ||
        require_ok("gyro power", bmi08g_set_power_mode(sensor)) ||
        require_ok("gyro measurement config", bmi08g_set_meas_conf(sensor)))
        return -1;
    delay_us(50000, NULL);
    if (require_ok("accel config readback", bmi08a_get_meas_conf(sensor)) ||
        require_ok("gyro config readback", bmi08g_get_meas_conf(sensor)) ||
        require_ok("accel power readback", bmi08a_get_power_mode(sensor)) ||
        require_ok("gyro power readback", bmi08g_get_power_mode(sensor)))
        return -1;
    if (sensor->accel_cfg.range != BMI088_ACCEL_RANGE_6G || sensor->accel_cfg.odr != BMI08_ACCEL_ODR_100_HZ ||
        sensor->accel_cfg.bw != BMI08_ACCEL_BW_NORMAL || sensor->accel_cfg.power != BMI08_ACCEL_PM_ACTIVE ||
        sensor->gyro_cfg.range != BMI08_GYRO_RANGE_500_DPS || sensor->gyro_cfg.odr != BMI08_GYRO_BW_12_ODR_100_HZ ||
        sensor->gyro_cfg.power != BMI08_GYRO_PM_NORMAL) {
        fprintf(stderr, "Sensor profile readback differs; refusing incorrectly scaled samples\n");
        return -1;
    }
    return stop_requested ? -1 : 0;
}

static int sleep_until(uint64_t deadline)
{
    struct timespec timestamp = {.tv_sec = (time_t)(deadline / UINT64_C(1000000000)),
                                 .tv_nsec = (long)(deadline % UINT64_C(1000000000))};
    int result;
    do {
        result = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &timestamp, NULL);
    } while (result == EINTR && !stop_requested);
    if (result != 0 && result != EINTR) {
        fprintf(stderr, "clock_nanosleep: %s\n", strerror(result));
        return -1;
    }
    return 0;
}

static int stream_samples(struct bmi08_dev *sensor, unsigned long count)
{
    const double accel_scale = 6.0 * 9.80665 / 32768.0;
    const double gyro_scale = 500.0 * 3.14159265358979323846 / (180.0 * 32768.0);
    uint64_t deadline = monotonic_ns();
    unsigned long overruns = 0;
    puts("{\"type\":\"profile\",\"sensor\":\"BMI088\",\"accel_address\":25,\"gyro_address\":104,"
         "\"sensor_odr_hz\":100,\"requested_host_poll_hz\":100,\"accel_range_g\":6,\"gyro_range_dps\":500,"
         "\"frame\":\"Bosch native axes\",\"synchronized\":false,\"timestamp_basis\":\"host read interval, CLOCK_MONOTONIC\"}");
    for (unsigned long index = 0; index < count && !stop_requested; ++index) {
        struct bmi08_sensor_data accel = {0}, gyro = {0};
        uint8_t accel_status = 0, gyro_status = 0;
        uint64_t accel_begin = monotonic_ns();
        if (require_ok("accel status", bmi08a_get_status(&accel_status, sensor)) ||
            require_ok("accel data", bmi08a_get_data(&accel, sensor)))
            return -1;
        uint64_t accel_end = monotonic_ns();
        uint64_t gyro_begin = monotonic_ns();
        if (require_ok("gyro status", bmi08g_get_data_int_status(&gyro_status, sensor)) ||
            require_ok("gyro data", bmi08g_get_data(&gyro, sensor)))
            return -1;
        uint64_t gyro_end = monotonic_ns();
        printf("{\"type\":\"sample\",\"index\":%lu,\"accel_read_begin_ns\":%" PRIu64 ",\"accel_read_end_ns\":%" PRIu64
               ",\"gyro_read_begin_ns\":%" PRIu64 ",\"gyro_read_end_ns\":%" PRIu64
               ",\"accel_ready\":%s,\"gyro_drdy_pulse\":%s,\"accel_raw\":[%d,%d,%d],\"gyro_raw\":[%d,%d,%d],"
               "\"accel_m_s2\":[%.8f,%.8f,%.8f],\"gyro_rad_s\":[%.8f,%.8f,%.8f],\"host_overruns\":%lu}\n",
               index, accel_begin, accel_end, gyro_begin, gyro_end,
               accel_status ? "true" : "false",
               (gyro_status & BMI08_GYRO_DATA_READY_INT) ? "true" : "false",
               (int)accel.x, (int)accel.y, (int)accel.z, (int)gyro.x, (int)gyro.y, (int)gyro.z,
               accel.x * accel_scale, accel.y * accel_scale, accel.z * accel_scale,
               gyro.x * gyro_scale, gyro.y * gyro_scale, gyro.z * gyro_scale, overruns);
        if (fflush(stdout) != 0) {
            perror("stdout");
            return -1;
        }
        deadline += SAMPLE_PERIOD_NS;
        if (gyro_end >= deadline) {
            ++overruns;
            deadline = gyro_end + SAMPLE_PERIOD_NS;
        }
        if (index + 1 < count && sleep_until(deadline) != 0)
            return -1;
    }
    return 0;
}

static void usage(FILE *output)
{
    fprintf(output, "Usage: bmi088-i2c --describe | --device /dev/i2c-N --probe | --device /dev/i2c-N --stream [--samples N]\n"
                    "--probe reads only the two chip IDs; --stream resets/configures the two BMI088 endpoints.\n"
                    "Addresses are fixed to this HAT: accel 0x19, gyro 0x68. Default stream: 100 samples at requested 100Hz.\n");
}

int main(int argc, char **argv)
{
    enum {MODE_NONE, MODE_PROBE, MODE_STREAM, MODE_DESCRIBE} mode = MODE_NONE;
    const char *device = NULL;
    unsigned long sample_count = 100;
    bool samples_given = false;
    const struct option options[] = {
        {"device", required_argument, NULL, 'd'}, {"probe", no_argument, NULL, 'p'},
        {"stream", no_argument, NULL, 's'}, {"samples", required_argument, NULL, 'n'},
        {"describe", no_argument, NULL, 'D'}, {"help", no_argument, NULL, 'h'}, {NULL, 0, NULL, 0}
    };
    int option;
    while ((option = getopt_long(argc, argv, "d:psn:Dh", options, NULL)) != -1) {
        if (option == 'h') {
            usage(stdout);
            return EXIT_SUCCESS;
        }
        if (option == 'd') {
            device = optarg;
        } else if (option == 'n') {
            char *end = NULL;
            errno = 0;
            sample_count = strtoul(optarg, &end, 10);
            if (errno || optarg[0] < '0' || optarg[0] > '9' || *end || sample_count == 0 || sample_count > 1000000) {
                fprintf(stderr, "--samples must be an integer in 1..1000000\n");
                return EXIT_FAILURE;
            }
            samples_given = true;
        } else if (option == 'p' || option == 's' || option == 'D') {
            if (mode != MODE_NONE) {
                usage(stderr);
                return EXIT_FAILURE;
            }
            mode = option == 'p' ? MODE_PROBE : option == 's' ? MODE_STREAM : MODE_DESCRIBE;
        } else {
            usage(stderr);
            return EXIT_FAILURE;
        }
    }
    if (optind != argc || mode == MODE_NONE || (samples_given && mode != MODE_STREAM) || (mode != MODE_DESCRIBE && device == NULL)) {
        usage(stderr);
        return EXIT_FAILURE;
    }
    if (mode == MODE_DESCRIBE) {
        printf("{\"sensor\":\"BMI088\",\"sdk_commit\":\"%s\",\"accel_address\":25,\"gyro_address\":104,"
               "\"expected_accel_id\":30,\"expected_gyro_id\":15,\"profile_odr_hz\":100,\"hardware_accessed\":false}\n", SDK_COMMIT);
        return EXIT_SUCCESS;
    }
    struct sigaction action = {.sa_handler = request_stop};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, NULL) != 0 || sigaction(SIGTERM, &action, NULL) != 0) {
        perror("sigaction");
        return EXIT_FAILURE;
    }
    struct endpoint accel = {.descriptor = -1, .address = ACCEL_ADDRESS};
    struct endpoint gyro = {.descriptor = -1, .address = GYRO_ADDRESS};
    int result = EXIT_FAILURE;
    if (open_endpoint(device, &accel, true) || open_endpoint(device, &gyro, false))
        goto cleanup;
    uint8_t accel_id = 0, gyro_id = 0;
    if (read_registers(BMI08_REG_ACCEL_CHIP_ID, &accel_id, 1, &accel) != BMI08_INTF_RET_SUCCESS ||
        read_registers(BMI08_REG_GYRO_CHIP_ID, &gyro_id, 1, &gyro) != BMI08_INTF_RET_SUCCESS)
        goto cleanup;
    bool identities_match = accel_id == BMI088_ACCEL_CHIP_ID && gyro_id == BMI08_GYRO_CHIP_ID;
    printf("{\"type\":\"identity\",\"accel_address\":25,\"gyro_address\":104,\"accel_chip_id\":%u,"
           "\"gyro_chip_id\":%u,\"identities_match\":%s}\n", accel_id, gyro_id, identities_match ? "true" : "false");
    if (!identities_match) {
        fprintf(stderr, "Both BMI088 identities must match before any configuration write\n");
        goto cleanup;
    }
    if (mode == MODE_PROBE) {
        result = EXIT_SUCCESS;
        goto cleanup;
    }
    struct bmi08_dev sensor = {0};
    sensor.variant = BMI088_VARIANT;
    sensor.intf = BMI08_I2C_INTF;
    sensor.intf_ptr_accel = &accel;
    sensor.intf_ptr_gyro = &gyro;
    sensor.read = read_registers;
    sensor.write = write_registers;
    sensor.delay_us = delay_us;
    sensor.read_write_len = TRANSFER_LIMIT;
    if (configure_sensor(&sensor) == 0 && stream_samples(&sensor, sample_count) == 0)
        result = EXIT_SUCCESS;
cleanup:
    if (gyro.descriptor >= 0)
        close(gyro.descriptor);
    if (accel.descriptor >= 0)
        close(accel.descriptor);
    return stop_requested ? 130 : result;
}
