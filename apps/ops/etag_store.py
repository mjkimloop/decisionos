# Backward compatibility shim: re-export from unified storage layer
from apps.storage.etag_store import *  # noqa: F401,F403

# Also keep existing interface for compatibility
from apps.ops.cache.etag_store import ETagStore as ETagStoreV2  # noqa: F401
from apps.ops.cache.etag_store import InMemoryETagStore as InMemoryETagStoreV2  # noqa: F401
from apps.ops.cache.etag_store import RedisETagStore as RedisETagStoreV2  # noqa: F401
from apps.ops.cache.etag_store import get_store  # noqa: F401
