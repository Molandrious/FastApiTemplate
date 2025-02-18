from src.transport.rest.router import FastAPILoggingRouter

debug_router = FastAPILoggingRouter(prefix='/debug', tags=['health'])


@debug_router.get(path='/health')
async def get_health_handler():
    return {'is_alive': True}


@debug_router.get(path='/ping')
async def get_ping_handler():
    return 'PONG'
