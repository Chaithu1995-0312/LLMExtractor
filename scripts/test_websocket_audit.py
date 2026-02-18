import socketio
import time
import json

def test_audit_stream():
    sio = socketio.Client()

    received_events = []

    @sio.on('connected')
    def on_connect(data):
        print(f"Connected: {data}")

    @sio.on('audit_event')
    def on_audit_event(data):
        print(f"Received event: {data['event']} from {data['component']}")
        received_events.append(data)

    try:
        print("Connecting to http://localhost:5001...")
        sio.connect('http://localhost:5001')
        
        print("Waiting for events (triggering a mock event in 2 seconds)...")
        time.sleep(2)
        
        # We need to trigger an audit event. 
        # Since we patched GraphManager._log_audit_event, any call to it should emit.
        from nexus.graph.manager import GraphManager
        from nexus.graph.schema import AuditEventType, DecisionAction
        
        gm = GraphManager()
        print("Triggering mock audit event...")
        gm._log_audit_event(
            event_type=AuditEventType.RUN_COMPILE_STARTED,
            agent="TestAgent",
            component="compiler",
            decision_action=DecisionAction.ACCEPTED,
            reason="Testing WebSocket broadcast"
        )
        
        time.sleep(2)
        
        if len(received_events) > 0:
            print(f"SUCCESS: Received {len(received_events)} events via WebSocket.")
        else:
            print("FAILURE: No events received via WebSocket.")
            
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        sio.disconnect()

if __name__ == "__main__":
    test_audit_stream()
