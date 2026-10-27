import json,os,sys,urllib.request,urllib.error
OPS=['create_project','rename_project','delete_project','restore','create_entry','rename_entry','delete_entry','set_flag','mark_complete','check','export','attach','move_invoice']
def call_api(body=None):
    base=os.environ.get('REIMBURSE_URL','http://127.0.0.1:8765').rstrip('/')
    if not base.startswith('http://127.0.0.1:'):raise ValueError('仅允许连接本机127.0.0.1接口')
    token=os.environ.get('REIMBURSE_TOKEN','')
    if not token:raise ValueError('请在客户端配置环境变量REIMBURSE_TOKEN')
    request=urllib.request.Request(base+('/v1/state' if body is None else '/v1/actions'),data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=30) as response:return json.loads(response.read())
    except urllib.error.HTTPError as e:raise ValueError(f'本机接口HTTP {e.code}: '+e.read().decode('utf-8',errors='replace')) from None
def handle(message):
    method=message.get('method');params=message.get('params',{})
    if method=='initialize':return dict(protocolVersion='2024-11-05',capabilities={'tools':{}},serverInfo=dict(name='CounterMiao',version='4.0'))
    if method=='ping':return {}
    if method=='tools/list':return dict(tools=[dict(name='reimbursement_state',description='读取当前报销批次、项目、报销项和发票摘要。',inputSchema={'type':'object','properties':{}}),dict(name='reimbursement_action',description='操作本机报销程序；删除可恢复，需程序允许写入。',inputSchema={'type':'object','properties':{'op':{'type':'string','enum':OPS},'project_id':{'type':'string'},'entry_id':{'type':'string'},'target_entry_id':{'type':'string'},'name':{'type':'string'},'kind':{'type':'string'},'flag':{'type':'string','enum':['red','hidden']},'value':{'type':'boolean'},'record_id':{'type':'string'},'output_dir':{'type':'string'},'label':{'type':'string'},'paths':{'type':'array','items':{'type':'string'}},'invoice_number':{'type':'string'}},'required':['op']})])
    if method=='tools/call':
        try:
            name=params.get('name')
            if name not in ['reimbursement_state','reimbursement_action']:raise ValueError('未知工具')
            result=call_api(None if name=='reimbursement_state' else params.get('arguments',{}));return dict(content=[dict(type='text',text=json.dumps(result,ensure_ascii=False))],isError=False)
        except Exception as e:return dict(content=[dict(type='text',text=str(e))],isError=True)
    raise ValueError('未知JSON-RPC方法')
def main():
    if hasattr(sys.stdin,'reconfigure'):sys.stdin.reconfigure(encoding='utf-8')
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    for line in sys.stdin:
        try:
            msg=json.loads(line)
            if 'id' not in msg:continue
            try:response=dict(jsonrpc='2.0',id=msg['id'],result=handle(msg))
            except Exception as e:response=dict(jsonrpc='2.0',id=msg['id'],error=dict(code=-32601,message=str(e)))
        except Exception:response=dict(jsonrpc='2.0',id=None,error=dict(code=-32700,message='Invalid JSON'))
        print(json.dumps(response,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
