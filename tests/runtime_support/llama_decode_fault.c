/* Test-only LD_PRELOAD interceptor for strict-cache qualification.
 *
 * With no absolute trigger path, every call is forwarded.  The injected
 * failure is process-wide and one-shot, so concurrent callers cannot multiply
 * the fault.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include "llama.h"

typedef int32_t (*llama_decode_fn)(struct llama_context *, struct llama_batch);

static pthread_once_t resolve_once = PTHREAD_ONCE_INIT;
static llama_decode_fn real_llama_decode;
static _Atomic int injected;

static void resolve_symbol(void) {
    dlerror();
    real_llama_decode = (llama_decode_fn)dlsym(RTLD_NEXT, "llama_decode");
    if (dlerror() != NULL) {
        real_llama_decode = NULL;
    }
}

static int trigger_present(void) {
    const char *path = getenv("SAEA_CACHE_DECODE_FAULT_TRIGGER");
    struct stat details;
    return path != NULL && path[0] == '/' && stat(path, &details) == 0 && S_ISREG(details.st_mode);
}

int32_t llama_decode(struct llama_context *ctx, struct llama_batch batch) {
    pthread_once(&resolve_once, resolve_symbol);

    if (batch.embd != NULL && trigger_present()) {
        int expected = 0;
        if (atomic_compare_exchange_strong(&injected, &expected, 1)) {
            fputs("SAEA_INJECTED_EMBEDDED_DECODE_FAILURE\n", stderr);
            fflush(stderr);
            return -1;
        }
    }

    if (real_llama_decode == NULL) {
        errno = ENOSYS;
        return -1;
    }
    return real_llama_decode(ctx, batch);
}
