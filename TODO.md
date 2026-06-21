# TODO - Real-time chat (Django Channels + Redis)

## Step 1: Inventory existing chat implementation
- [x] Inspect ChatMessage model and existing HTTP send_chat_message view.
- [x] Inspect customer_dashboard.html chat section.

## Step 2: Design Channels layer (no DB/model/url changes)
- [ ] Implement hyperlocal_marketplace routing + consumers for websocket chat (room per sender/receiver pair).
- [ ] Decide websocket URL pattern that can derive conversation participants from URL.


## Step 3: Update ASGI to mount websocket routing alongside HTTP
- [ ] Modify hyperlocal_marketplace/asgi.py to use ProtocolTypeRouter and URLRouter.

## Step 4: Wire template JavaScript
- [ ] Add minimal JS to open WS, send messages, and append incoming messages.
- [ ] Ensure CSRF/auth works (likely use session cookie via AuthMiddlewareStack).

## Step 5: Ensure message persistence + real-time delivery
- [ ] Consumers will create ChatMessage on receive, then broadcast to the same room.
- [ ] Consumers will also send existing conversation messages on connect (optional but helpful).

## Step 6: Test scenarios
- [ ] Two different clients on same Django server: verify instant delivery.
- [ ] Verify existing HTTP chat send continues working (preserve functionality).


