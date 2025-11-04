from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from app.dependencies import templates
import threading
import socket
import select
import time

router = APIRouter(prefix="/laser", tags=["laser"])

is_listening = False
udp_thread = None
web_messages = []


def add_message(message):
    timestamp = time.strftime("%H:%M:%S")
    web_messages.append(f"[{timestamp}] {message}")
    if len(web_messages) > 20:
        web_messages.pop(0)


def udp_listener():
    global is_listening

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", 8888))
    sock.setblocking(False)

    add_message("UDP listener started on port 8888")

    while is_listening:
        ready_to_read, _, _ = select.select([sock], [], [], 0.5)
        if ready_to_read:
            data, addr = sock.recvfrom(8)
            packet_value = int.from_bytes(data, 'big')

            if packet_value == 255:
                add_message(f"Пойман пакет TOKAMAK START (255) от {addr[0]}")
            elif packet_value == 127:
                add_message(f"Пойман пакет TOKAMAK COUNTDOWN (127) от {addr[0]}")
            else:
                add_message(f"Пойман пакет: {packet_value} от {addr[0]}")

    sock.close()
    add_message("UDP listener stopped")


@router.get("/", response_class=HTMLResponse)
async def laser_control_page(request: Request):
    return templates.TemplateResponse("laser.html", {
        "request": request,
        "messages": web_messages
    })


@router.get("/messages")
async def get_messages():
    return JSONResponse(web_messages)


@router.post("/arm")
async def arm_laser():
    add_message("ARM button pressed")
    return JSONResponse({"status": "success", "message": "Laser armed"})


@router.post("/disarm")
async def disarm_laser():
    add_message("DISARM button pressed")
    return JSONResponse({"status": "success", "message": "Laser disarmed"})


@router.post("/fire")
async def fire_laser():
    add_message("FIRE button pressed")
    return JSONResponse({"status": "success", "message": "Laser firing"})


@router.post("/stop")
async def stop_laser():
    add_message("STOP button pressed")
    return JSONResponse({"status": "success", "message": "Laser stopped"})


@router.post("/toggle-ready")
async def toggle_ready(ready: bool = Form(...)):
    global is_listening, udp_thread

    if ready:
        is_listening = True
        udp_thread = threading.Thread(target=udp_listener)
        udp_thread.start()
        add_message("Ready mode ON - Listening for UDP packets")
        return JSONResponse({"status": "success", "message": "Ready - Listening UDP port 8888"})
    else:
        is_listening = False
        if udp_thread:
            udp_thread.join()
        add_message("Ready mode OFF - UDP stopped")
        return JSONResponse({"status": "success", "message": "Not ready - UDP stopped"})


@router.post("/send-test-packet")
async def send_test_packet(request: dict):
    packet_value = request.get("packet_value", 255)

    add_message(f"Sent test packet: {packet_value}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    data = packet_value.to_bytes(8, 'big')
    sock.sendto(data, ('255.255.255.255', 8888))
    sock.close()

    return JSONResponse({"status": "success", "message": f"Test packet {packet_value} sent"})
