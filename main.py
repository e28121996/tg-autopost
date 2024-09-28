"""Skrip utama untuk bot auto-posting Telegram."""

import contextlib
from typing import Optional

import asyncio
from telethon import TelegramClient

from src.auth import create_client
from src.cache import cache
from src.config import yaml_config
from src.error_handler import send_critical_error_notification
from src.group_manager import group_manager
from src.logger import logger
from src.message_manager import message_manager
from src.message_sender import send_mass_message
from src.scheduler import scheduler


async def send_scheduled_messages(client: TelegramClient) -> None:
    """
    Mengirim pesan terjadwal ke grup-grup yang valid.

    Args:
        client (TelegramClient): Klien Telegram yang digunakan untuk mengirim pesan.

    Raises:
        Exception: Jika terjadi kesalahan saat mengirim pesan.
    """
    try:
        groups = group_manager.get_valid_groups()
        message = message_manager.get_random_message()
        await send_mass_message(client, groups, message)
    except Exception as e:
        logger.error(f"Kesalahan dalam send_scheduled_messages: {e}")


async def clear_cache_periodically() -> None:
    """
    Membersihkan entri cache yang kedaluwarsa secara berkala.

    Raises:
        Exception: Jika terjadi kesalahan saat membersihkan cache.
    """
    while True:
        try:
            await asyncio.sleep(yaml_config["cache_expiry"])
            cache.clear_expired()
            logger.info("Entri cache yang kedaluwarsa telah dibersihkan")
        except Exception as e:
            logger.error(f"Kesalahan dalam clear_cache_periodically: {e}")


async def main() -> None:
    """
    Menjalankan loop utama bot.

    Raises:
        KeyboardInterrupt: Jika bot dihentikan oleh pengguna.
        Exception: Jika terjadi kesalahan tak terduga dalam loop utama.
    """
    client: Optional[TelegramClient] = None
    try:
        client = await create_client()
        logger.info("Bot dimulai")

        # Menambahkan tugas pengiriman pesan terjadwal ke scheduler
        scheduler.add_task(lambda: send_scheduled_messages(client))

        # Menjalankan scheduler dan pembersihan cache secara bersamaan
        await asyncio.gather(scheduler.run(), clear_cache_periodically())
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh pengguna")
    except Exception as e:
        error_message = f"Kesalahan tak terduga dalam loop utama: {e}"
        logger.error(error_message)
        if client:  # Memeriksa apakah client telah diinisialisasi
            await send_critical_error_notification(client, error_message)
        else:
            logger.error(
                "Tidak dapat mengirim notifikasi kesalahan kritis: Client adalah None"
            )
    finally:
        if client and client.is_connected():
            with contextlib.suppress(Exception):
                await client.disconnect()  # type: ignore
            logger.info("Client terputus")


if __name__ == "__main__":
    asyncio.run(main())
