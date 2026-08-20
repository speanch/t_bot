from aiogram import Router

from handlers import common, fitting

router = Router()
router.include_router(common.router)
router.include_router(fitting.router)
