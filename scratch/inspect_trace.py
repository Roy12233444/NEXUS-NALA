import queue
import traceback
from nala_server.contracts import TaskRequest, ExecutionMode
from nala_server.state import RuntimeState
from nala_server.nala_runner import build_nala_runner
from nala_server.handlers import custom_step_handler

rs = RuntimeState()
req = TaskRequest(
    task_id='t1',
    session_id='s1',
    prompt='create a file named nala_srv001_proof.txt containing: NALA SRV001 NEW RUNTIME VERIFIED',
    mode=ExecutionMode.AUTONOMOUS
)
rs.create_task(req)
q = queue.Queue()
runner = build_nala_runner(state=rs, legacy_step_handler=custom_step_handler, event_queue=q)
runner.start('t1')
runner.wait('t1', timeout=5.0)

while not q.empty():
    ev_type, payload, s_id = q.get()
    print(f"--- EVENT: {ev_type} ---")
    print("Message:", payload.get('message'))
    if 'data' in payload and 'traceback' in payload['data']:
        print("TRACEBACK:\n", payload['data']['traceback'])
