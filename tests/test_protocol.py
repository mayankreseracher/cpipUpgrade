import time
from shared.protocol import RPCMessage, MessageType, make_call, make_result, make_error


def test_rpc_message_timestamp_preservation():
    """Test that RPCMessage preserves timestamp when deserialized."""
    orig = RPCMessage(
        type=MessageType.CALL,
        method="test.method",
        params={"a": 1},
        timestamp=123456789.0
    )
    assert orig.timestamp == 123456789.0
    
    serialized = orig.to_dict()
    assert serialized["timestamp"] == 123456789.0
    
    deserialized = RPCMessage.from_dict(serialized)
    assert deserialized.timestamp == 123456789.0


def test_make_call_empty_params():
    """Test that make_call handles empty parameters dict correctly."""
    # Case 1: explicit empty params
    msg1 = make_call("some.method", params={})
    assert msg1.params == {}
    
    # Case 2: kwargs fallback
    msg2 = make_call("some.method", key="value")
    assert msg2.params == {"key": "value"}
    
    # Case 3: both (params takes precedence)
    msg3 = make_call("some.method", params={"a": 1}, b=2)
    assert msg3.params == {"a": 1}
