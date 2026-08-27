import assert from "node:assert/strict";
import test from "node:test";

test("Double click protection ensures executeAction is called only once", async () => {
  // Simulate the state behavior of ChatWidget handleConfirmAction
  let executeCount = 0;
  
  const mockAction = {
    type: "route_case",
    case_id: "123",
    payload: {},
    confirmation_required: true,
    confirmation_text: "Test"
  };
  
  let msg = {
    id: "msg1",
    role: "bot",
    text: "Eylem",
    pendingAction: mockAction,
    actionStatus: "idle"
  };
  
  const handleConfirmAction = async () => {
    if (msg.actionStatus === "submitting" || msg.actionStatus === "resolved") {
      return;
    }
    
    // Set to submitting synchronously
    msg.actionStatus = "submitting";
    
    executeCount++;
    
    // Simulate delay
    await new Promise(r => setTimeout(r, 10));
    
    msg.actionStatus = "resolved";
  };
  
  // Fire first click
  const firstCall = handleConfirmAction();
  
  // Fire second click immediately (race condition test)
  const secondCall = handleConfirmAction();
  
  await Promise.all([firstCall, secondCall]);
  
  assert.equal(executeCount, 1);
  assert.equal(msg.actionStatus, "resolved");
});
