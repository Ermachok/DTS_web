import socket
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_command(server_address, command, command_name, timeout=2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(server_address)
        sock.send(command)
        logger.info(f'Sent {command_name}')
        answer_serv = sock.recv(1024)
        logger.info(f'Received: {answer_serv}')

        return answer_serv
    except Exception as e:
        logger.error(f'Error sending {command_name}: {e}')
        raise TimeoutError(f'Cannot connect to laser: {e}')
    finally:
        sock.close()


def arm(server_address, timeout=2):
    try:
        send_command(server_address, b'\x23\x03\x53\x00\x79', 'idling on', timeout)
        return True
    except TimeoutError as e:
        logger.error(f'Arming failed: {e}')
        raise


def start(server_address, timeout=2):
    try:
        send_command(server_address, b'\x23\x03\x43\x00\x69', 'start', timeout)
        return True
    except TimeoutError as e:
        logger.error(f'Start pumping failed: {e}')
        raise


def disarm(server_address, timeout=2):
    try:
        send_command(server_address, b'\x23\x03\x73\x00\x99', 'idling off', timeout)
        return True
    except TimeoutError as e:
        logger.error(f'Disarming failed: {e}')
        raise


def stop(server_address, timeout=2):
    try:
        send_command(server_address, b'\x23\x03\x44\x00\x70', 'stop', timeout)
        return True
    except TimeoutError as e:
        logger.error(f'Disarming failed: {e}')
        raise


def fire(server_address):
    try:
        send_command(server_address, b'\x23\x03\x42\x00\x68', 'laser generator on')
    except TimeoutError as e:
        logger.error(f'Firing failed: {e}')
        raise


def fire_stop(server_address):
    try:
        send_command(server_address, b'\x23\x03\x62\x00\x88', 'laser generator off')
    except TimeoutError as e:
        logger.error(f'Stopping fire failed: {e}')
        raise
