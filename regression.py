import copy,json,os,time,hashlib,zipfile
from pathlib import Path
from decimal import Decimal
from xml.etree import ElementTree as ET
import app
import domain as D
import legacy

def run(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True);results=[]
    def check(x,label):assert x,label;results.append(label)
    pdf=root/'模拟发票.pdf';doc=legacy.pymupdf.open();page=doc.new_page()
    for y,text in [(40,'发票号码：12345678901234567890'),(70,'深圳科创学院'),(100,'开票日期：2026年10月01日'),(130,'（小写）￥600.00')]:page.insert_text((30,y),text,fontname='china-s',fontsize=12)
    doc.save(pdf);doc.close();raw=app.extract(pdf);check(raw['date']=='2026-10-01' and raw['amount']=='600.00','识别发票金额、号码与开票日期')
    def inv(amount='600',number=None,seller='供应商甲',tax='TAX_A',date='2026-10-01',count=1):
        x=copy.deepcopy(raw);cents=int(legacy.money(amount)*100);parts=[cents//count]*count;parts[-1]+=cents-sum(parts)
        x.update(number=number or D.uid(),amount=amount,seller=seller,seller_tax=tax,date=date,confirmed=True,category='采购',photos=[],items=[dict(name='测试项目'+str(n),model='型号',qty='1',amount=str(Decimal(v)/100)) for n,v in enumerate(parts)])
        return x
    p=D.project('项目甲');q=D.project('项目乙');projects=[p,q]
    p['types']['零星采购']['invoices']=[inv('600')];q['types']['零星采购']['invoices']=[inv('400')]
    check(not D.monthly_issues(projects),'跨项目同供应商自然月累计恰好1000通过')
    q['types']['零星采购']['invoices'][0]['amount']='400.01'
    check(len(D.monthly_issues(projects))==2 and not D.plan(projects,p,'零星采购')[0],'超过1000时关联的全部发票提示并阻止分单规避')
    q['types']['零星采购']['invoices'][0]['date']='2026-11-01';check(not D.monthly_issues(projects),'相邻自然月分别统计')
    q['types']['零星采购']['invoices'][0].update(date='2025-10-01');check(not D.monthly_issues(projects),'不同年份同月份不混算')
    q['types']['零星采购']['invoices'][0].update(date='2026-10-01',seller_tax='TAX_B');check(not D.monthly_issues(projects),'不同供应商税号分别统计')
    q['types']['零星采购']['invoices'][0].update(seller_tax='',seller='供应商甲');check(len(D.monthly_issues(projects))==2,'税号缺失但名称相同可关联已知税号')
    p['types']['零星采购']['invoices']=[inv('100',number='N'+str(n)) for n in range(10)];q['types']['零星采购']['invoices']=[]
    check(not D.monthly_issues(projects),'同月发票张数不限，十张共1000通过')
    p['types']['零星采购']['invoices'][0]['date']='';check(bool(D.monthly_issues(projects)),'缺少开票日期提示补充，不能跳过月检查')
    p['types']['零星采购']['invoices']=[inv('1001')];check(bool(D.plan(projects,p,'零星采购')[1]),'零星采购单票超过1000拦截')
    p['types']['零星采购']['invoices']=[inv('1000',seller=f'厂{n}',tax=f'T{n}') for n in range(6)]
    b,_=D.plan(projects,p,'零星采购');check(len(b)==2 and max(x['amount'] for x in b)<=5000,'不同供应商零星采购按每单5000分组')
    p['types']['零星采购']['invoices']=[inv('100',count=15),inv('10',tax='OTHER')]
    b,_=D.plan(projects,p,'零星采购');check(len(b)==2,'15个实际采购项目上限')
    for kind in ['服务采购','物资采购']:
        p['types'][kind]['invoices']=[inv('2500'),inv('2500')]
    check(len(D.plan(projects,p,'服务采购')[0])==2,'服务采购一票一单，不合并')
    check(len(D.plan(projects,p,'物资采购')[0])==1,'物资采购允许超过1000并在5000内合单')
    p['types']['服务采购']['invoices']=[inv('5000.01')];check(bool(D.plan(projects,p,'服务采购')[1]),'服务单票超过5000拦截')
    p['types']['物资采购']['invoices']=[inv('5000')];check(not D.plan(projects,p,'物资采购')[1],'物资采购5000边界通过')
    travel=inv('123456.78');travel['items']=[];p['types']['差旅报销']['invoices']=[travel]
    check(D.plan(projects,p,'差旅报销')[0][0]['amount']==Decimal('123456.78'),'差旅无金额限制，无采购明细也可生成表格')
    p=D.project('完整项目');projects=[p];p['types']['零星采购']['invoices']=[inv('300')]
    errors,_=D.inspect_project(projects,p)
    check(any('签字' in e for e in errors) and not any('采购申请' in e or '入库' in e for e in errors),'零星采购只要求发票和逐份签字验收单')
    b,_=D.plan(projects,p,'零星采购');bid=b[0]['id'];p['types']['零星采购']['signed'][bid]=[str(pdf)]
    check(not D.inspect_project(projects,p)[0],'无配图项目在签字件齐全后通过')
    p['types']['零星采购']['invoices'][0]['items'][0]['model']='新型号';check(any('签字' in e for e in D.inspect_project(projects,p)[0]),'更改明细后旧签字件不能冒充新验收单')
    p['types']['零星采购']['invoices'][0]['items'][0]['model']='型号'
    p['types']['服务采购']['invoices']=[inv('2500')];p['types']['物资采购']['invoices']=[inv('2500')];p['types']['差旅报销']['invoices']=[travel]
    for kind in ['服务采购','物资采购','差旅报销']:
        t=p['types'][kind]
        for key in D.REQUIRED[kind]:t['attachments'][key]=[str(pdf)]
        if kind!='差旅报销':
            for batch in D.plan(projects,p,kind)[0]:t['signed'][batch['id']]=[str(pdf)]
    check(not D.inspect_project(projects,p)[0],'四类报销各自必需附件齐全后检查通过')
    p['types']['差旅报销']['attachments']['行程申请']=[];p['manual_complete']=True
    check(bool(D.inspect_project(projects,p)[0]),'手动完成不伪造自动检查通过')
    p['types']['差旅报销']['attachments']['行程申请']=[str(pdf)]
    empty=root/'空附件.pdf';empty.write_bytes(b'');p['types']['物资采购']['attachments']['采购入库材料']=[str(empty)]
    check(any('入库' in e for e in D.inspect_project(projects,p)[0]),'空文件不算附件齐全')
    p['types']['物资采购']['attachments']['采购入库材料']=[str(pdf)]
    q=D.project('同票项目');q['types']['差旅报销']['invoices']=[copy.deepcopy(travel)]
    check(any('重复' in e for e in D.inspect_project([p,q],p)[0]),'跨项目重复发票占用提示')
    before=hashlib.sha256(pdf.read_bytes()).hexdigest();dest=D.export_all([p],root)
    check(hashlib.sha256(pdf.read_bytes()).hexdigest()==before,'归档复制原件，原文件内容不变')
    check((dest/'待报销项目文件表.xlsx').is_file() and (dest/'项目数据.json').is_file(),'输出待报销文件表及可恢复项目数据')
    with zipfile.ZipFile(dest/'待报销项目文件表.xlsx') as z:
        check(z.testzip() is None and len([n for n in z.namelist() if n.startswith('xl/worksheets/')])==3,'项目总览、发票明细、附件索引三张表结构完整')
        for name in z.namelist():
            if name.endswith('.xml') or name.endswith('.rels'):ET.fromstring(z.read(name))
    with zipfile.ZipFile(str(dest)+'.zip') as z:check(z.testzip() is None,'最终材料ZIP完整性')
    check(not list(dest.rglob('图片')),'无图项目不创建图片空目录')
    check(len(list(dest.rglob('差旅报销表.xlsx')))==1,'差旅输出表格且不生成采购验收单')
    ui=app.App(root/'测试项目库',prompt_language=False);ui.withdraw()
    try:
        check(ui.title().startswith('CounterMiao') and (legacy.BASE/'CounterMiao.ico').is_file() and (legacy.BASE/'CounterMiao.png').is_file(),'CounterMiao名称、窗口图标及品牌资源已内置')
        popup=app.tk.Toplevel(ui);popup.withdraw();popup.title('选择报销条目类型')
        app.ttk.Combobox(popup,values=D.KINDS,state='readonly').pack()
        ui.language='zh';ui.localize_tick();changes={'title':0,'values':0,'selection':0}
        old_title=popup.title;old_config=ui.kind_choice.configure;old_set=ui.kind_choice.set
        def title(*args):
            if args:changes['title']+=1
            return old_title(*args)
        def configure(*args,**kw):
            if 'values' in kw:changes['values']+=1
            return old_config(*args,**kw)
        def select(value):changes['selection']+=1;return old_set(value)
        popup.title=title;ui.kind_choice.configure=configure;ui.kind_choice.set=select
        try:
            for _ in range(5):ui.localize_tick()
            check(changes=={'title':0,'values':0,'selection':0},'语言未改变时不重复设置弹窗标题、选项和选中值，避免选择栏闪烁')
        finally:popup.destroy();ui.kind_choice.configure=old_config;ui.kind_choice.set=old_set
        labels=[]
        def scan(widget):
            for child in widget.winfo_children():
                if isinstance(child,app.ttk.Button):labels.append(child.cget('text'))
                scan(child)
        scan(ui)
        check('新建报销项' in labels and '新建报销条目' in labels,'报销项与其下的报销条目使用不同的新建名称')
        wizard=ui.new_project();check(str(wizard.name_entry.cget('state'))=='disabled','新建报销项先选类型，未选时名称输入框不可填写')
        wizard.kind_var.set('服务采购');check(str(wizard.name_entry.cget('state'))=='normal','选择报销类型后才开放名称输入')
        wizard.name_var.set('服务合同报销');wizard.create_button.invoke();check(ui.current()['kind']=='服务采购' and ui.current()['name']=='服务合同报销','新建报销项同时保存名称与固定类型')
        original_ask=app.simpledialog.askstring;app.simpledialog.askstring=lambda *args,**kw:'结构设计服务条目'
        try:ui.new_entry()
        finally:app.simpledialog.askstring=original_ask
        check(ui.current_entry()['kind']=='服务采购' and ui.kind=='服务采购','新建条目继承所属报销项类型，不再另选类型')
        check(len(ui.tabs.tabs())==3 and str(ui.entry_name_input.cget('state'))=='normal','点击条目后有名称编辑和发票、配图、附件三个工作页签')
        ui.entry_name_var.set('结构设计服务（修改后）');ui.entry_notes_var.set('用户实际修改用途说明');ui.save_entry_button.invoke()
        check(ui.current_entry()['name']=='结构设计服务（修改后）' and ui.current_entry()['notes']=='用户实际修改用途说明','条目编辑区可修改名称和用途并保存')
        ui.invoices.append(inv('4500'));ui.refresh();ui.tree.selection_set('0');ui.update();review=ui.edit();review.invoice_fields['seller'].set('已更正的服务供应商');review.save_review()
        check(ui.invoices[0]['seller']=='已更正的服务供应商','发票内容修改入口可实际打开、修改并保存')
        sample_photo=root/'条目配图.png';legacy.Image.new('RGB',(300,200),'#217346').save(sample_photo)
        ui.attach_photo_paths(0,[str(sample_photo)]);check(len(ui.invoices[0]['photos'])==1 and bool(ui._photo_rows),'可从条目工作区直接添加发票配图并显示')
        ui.attach_entry_paths('attachments','服务类采购申请',[str(pdf)]);check(bool(ui.current_entry()['attachments']['服务类采购申请']) and bool(ui._attachment_rows),'可从条目工作区直接添加其他必需附件并显示')
        inherited_rejected=False
        try:ui.execute_action(dict(op='create_entry',project_id=ui.current()['id'],name='错误类型条目',kind='差旅报销'))
        except ValueError:inherited_rejected=True
        check(inherited_rejected,'外部AI也不能在服务报销项下创建不同类型条目')
        ui.projects=[p,q];ui.index=0;ui.bind_project();ui.update();check(ui.current()['id']==p['id'],'多项目界面绑定与实时金额刷新')
        restored=ui.read_state(dest/'项目数据.json');check(all(D.readable(i['source']) for _,_,i in D.all_invoices(restored)),'归档项目相对路径可重新加载')
        ui.projects=restored;ui.index=0;ui.bind_project();check(not D.inspect_project(restored,restored[0])[0],'重载归档后签字件及附件关系保留')
        ui.persist();check(ui.state_file.is_file(),'项目库自动保存')
        ui.projects=[D.project('整批导入测试')];ui.projects[0]['entries']=[D.entry('传感器采购','零星采购')];ui.index=0;ui.kind='零星采购';ui.entry_id=None;ui.bind_project();ui.import_paths([str(pdf)])
        deadline=time.monotonic()+30
        while ui.importing and time.monotonic()<deadline:ui.update();time.sleep(.03)
        check(not ui.importing and len(ui.invoices)==1 and Path(ui.invoices[0]['source']).is_relative_to(ui.data_dir),'后台导入的发票复制到项目资料目录后保存')
        called=[];ui.import_paths=lambda inputs:called.extend(inputs)
        from types import SimpleNamespace
        payload=ui.tk.call('format','%s',ui.tk.call('list',str(root)))
        ui.on_drop(SimpleNamespace(data=payload));check(called==[str(root)],'新版本保留中文目录原生拖放入口')
        travel_parent=D.project('差旅类型报销项','差旅报销');ui.projects=[travel_parent];ui.index=0;ui.kind='差旅报销';ui.entry_id=None;ui.bind_project();check('不限' in ui.rule.get(),'差旅界面明确无金额及数量上限')
        # Batch -> projects -> named entries -> materials, including visibility and reversible operations.
        p=D.project('树形项目');e1=D.entry('第一批零件','零星采购');e2=D.entry('第二批零件','零星采购')
        e1['invoices']=[inv('400',tax='TREE_A')];e2['invoices']=[inv('500',tax='TREE_B')];p['entries']=[e1,e2]
        ui.projects=[p];ui.index=0;ui.kind='零星采购';ui.entry_id=e1['id'];ui.bind_project();ui.update()
        check(ui.nav.parent('p:'+p['id'])=='b:'+ui.batch['id'] and ui.nav.parent('e:'+e1['id'])=='p:'+p['id'],'常驻树形栏按批次→项目→报销项建立真实父子层级')
        ui.nav.selection_set('e:'+e2['id']);ui.update();check(ui.entry_id==e2['id'] and ui.invoices is e2['invoices'],'模拟点击树形报销项后正确切换，刷新不递归触发选择')
        ui.entry_notes_var.set('切换前未手动保存的用途');ui.tabs.select(2)
        from types import SimpleNamespace
        old_identify=ui.nav.identify_row;ui.nav.identify_row=lambda y:'e:'+e1['id']
        try:ui.click_entry(SimpleNamespace(y=0));ui.update()
        finally:ui.nav.identify_row=old_identify
        check(ui.entry_id==e1['id'] and ui._workspace_id==e1['id'] and ui.entry_name_var.get()==e1['name'] and ui.tabs.index(ui.tabs.select())==0,'单击具体条目直接切换编辑区与发票页，无需下拉重新选择')
        check(e2.get('notes')=='切换前未手动保存的用途','点击切换前自动保留原条目的用途修改')
        ui.nav.selection_set('p:'+p['id']);ui.tree_select();ui.update()
        check(ui.view_mode=='project' and len(ui.overview_rows)==2,'点击报销项展示全部条目的表格总览')
        original_seller=e2['invoices'][0].get('seller','');original_confirmed=e2['invoices'][0].get('confirmed',False)
        ui.set_overview_value(e2,0,'company','统一表格企业');ui.set_overview_value(e2,0,'notes','统一表格用途')
        check(e2['invoices'][0]['seller']=='统一表格企业' and e2['notes']=='统一表格用途','统一表格可直接修改企业名称和条目用途')
        e2['invoices'][0].update(seller=original_seller,confirmed=original_confirmed)
        route=[];old_add=ui.add;old_row=ui.overview_table.identify_row;old_column=ui.overview_table.identify_column
        ui.add=lambda:route.append(ui.entry_id);ui.overview_table.identify_row=lambda y:e2['id']+':0';ui.overview_table.identify_column=lambda x:'#3'
        try:ui.overview_upload(e2['id']+':0','invoice')
        finally:ui.add=old_add;ui.overview_table.identify_row=old_row;ui.overview_table.identify_column=old_column
        check(route==[e2['id']] and ui.view_mode=='project','统一表格发票上传入口准确路由到对应条目且保留总览')
        ui.nav.selection_set('e:'+e1['id']);ui.tree_select();ui.update();check(ui.view_mode=='entry' and ui._workspace_id==e1['id'],'从总览点击具体条目立即切换该条目编辑区')
        ui.nav.item('p:'+p['id'],open=False);ui.refresh();check(not ui.nav.item('p:'+p['id'],'open'),'刷新保留用户折叠项目的状态')
        ui.entry_id=e1['id'];ui.bind_project()
        check(ui.invoices is e1['invoices'] and e1['invoices'][0]['entry_name']=='第一批零件','发票归属当前有名称的报销项')
        b,_=D.plan(ui.projects,p,'零星采购');check(len(b)==1 and len(b[0]['invoices'])==2,'多个小报销项按同类规则合并一份验收单')
        ui.execute_action(dict(op='set_flag',project_id=p['id'],entry_id=e1['id'],flag='red',value=True));check('red' in ui.nav.item('e:'+e1['id'],'tags'),'报销项可标红')
        ui.execute_action(dict(op='set_flag',project_id=p['id'],entry_id=e1['id'],flag='hidden',value=True));check(not ui.nav.exists('e:'+e1['id']),'隐藏报销项只隐藏视图，数据保留')
        ui.show_hidden.set(True);ui.rebuild_tree();check(ui.nav.exists('e:'+e1['id']),'显示隐藏项可找回节点')
        ui.execute_action(dict(op='delete_entry',project_id=p['id'],entry_id=e2['id']));check(e2 not in p['entries'] and ui.deleted_records,'报销项删除进入回收站')
        ui.execute_action(dict(op='restore',record_id=e2['id']));check(any(v['id']==e2['id'] for v in p['entries']),'被删除报销项可恢复')
        import batchfile,ai_control,mcp_adapter
        ui.execute_action(dict(op='delete_entry',project_id=p['id'],entry_id=e2['id']))
        packed=root/'可移动批次.reimbatch';batchfile.save_batch(packed,ui.batch,ui.projects,ui.deleted_records)
        moved=root/'其他文件夹';moved.mkdir();target=moved/packed.name;packed.rename(target)
        opened=batchfile.open_batch(target,ui.data_dir);loaded=ui.read_state(opened)
        check(all(D.readable(i['source']) for _,_,i in D.all_invoices(loaded)),'单文件批次移动位置后仍可恢复内置发票')
        check(loaded[0]['entries'][0]['name']=='第一批零件','批次恢复保留小报销项名称与层级')
        check(all(D.readable(i['source']) for r in ui.deleted_records for i in r.get('invoices',[])),'回收站中的材料随单文件批次恢复并可继续找回')
        ui.execute_action(dict(op='restore',record_id=e2['id']))
        with zipfile.ZipFile(target) as z:check(not any('AI设置' in n for n in z.namelist()),'批次不打包API Key或本机控制令牌')
        unsafe=root/'越界批次.reimbatch'
        with zipfile.ZipFile(unsafe,'w') as z:z.writestr('项目数据.json','{}');z.writestr('../escape.txt','bad')
        rejected=False
        try:batchfile.open_batch(unsafe,ui.data_dir)
        except ValueError:rejected=True
        check(rejected,'拒绝包含目录越界路径的批次文件')
        protected=ai_control.protect('FAKE_TEST_KEY');check('FAKE_TEST_KEY' not in protected and ai_control.protect(protected,True)=='FAKE_TEST_KEY','Windows用户加密保存并解密测试密钥')
        from urllib import request,error
        import secrets
        calls=[];token=secrets.token_urlsafe(16);api=ai_control.LocalAPI(token,lambda action:(calls.append(action) or {'ok':True}),port=0)
        try:
            base=f'http://127.0.0.1:{api.port}'
            unauthorized=False
            try:request.urlopen(base+'/v1/state')
            except error.HTTPError as ex:unauthorized=ex.code==401
            check(unauthorized,'本机AI接口拒绝无访问令牌的请求')
            req=request.Request(base+'/v1/state',headers={'Authorization':'Bearer '+token});check(json.loads(request.urlopen(req).read())['ok'],'本机AI接口通过令牌鉴权读取')
            blocked=False
            try:request.urlopen(request.Request(base+'/v1/actions',data=b'{"op":"create_project","name":"test"}',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}))
            except error.HTTPError as ex:blocked=ex.code==403
            check(blocked,'默认只读接口不允许AI修改或删除')
            api.allow_write=True;req=request.Request(base+'/v1/actions',data=b'{"op":"create_project","name":"test"}',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'});check(json.loads(request.urlopen(req).read())['ok'],'明确启用写入后接受结构化操作')
            originblocked=False
            try:request.urlopen(request.Request(base+'/v1/state',headers={'Authorization':'Bearer '+token,'Origin':'https://example.invalid'}))
            except error.HTTPError as ex:originblocked=ex.code==403
            check(originblocked,'本机操作接口拒绝网页跨域来源')
        finally:api.close()
        check(len(mcp_adapter.handle(dict(method='tools/list'))['tools'])==2,'MCP接口提供状态读取和结构化操作工具')
        check('tools' in mcp_adapter.handle(dict(method='initialize'))['capabilities'],'MCP初始化握手返回工具能力')
        # User personas: save/reopen, audit/review, automation and close cancellation.
        encrypted=root/'加密批次.reimbatch';ui.persist();batchfile.save_batch(encrypted,ui.batch,ui.projects,password='TestPassword_123',history=ui.history)
        check(batchfile.is_encrypted(encrypted) and not zipfile.is_zipfile(encrypted),'密码批次使用认证加密，不能作为普通ZIP直接查看')
        wrong=False
        try:batchfile.open_batch(encrypted,ui.data_dir,'wrong_password')
        except ValueError:wrong=True
        check(wrong,'错误密码无法解密批次')
        decrypted=batchfile.open_batch(encrypted,ui.data_dir,'TestPassword_123');check(json.loads(decrypted.read_text(encoding='utf-8'))['history']==ui.history,'正确密码恢复材料及内部修改记录')
        tampered=root/'被改动批次.reimbatch';bytes_=bytearray(encrypted.read_bytes());bytes_[-1]^=1;tampered.write_bytes(bytes_)
        rejected=False
        try:batchfile.open_batch(tampered,ui.data_dir,'TestPassword_123')
        except ValueError:rejected=True
        check(rejected,'加密文件被篡改后认证校验失败')
        previous=len(ui.history);ui.current()['name']='用户审核后的项目';ui.refresh();check(len(ui.history)>previous and ui.history[-1]['changes'],'项目修改自动生成含前后哈希及变更路径的记录')
        ui.settings['autosave_minutes']=0;ui.schedule_autosave();check(ui.autosave_timer is None,'关闭自动保存会取消计时器')
        ui.settings['autosave_minutes']=1.5;ui.schedule_autosave();check(ui.autosave_timer is not None,'支持自定义分钟数自动保存')
        ui.batch_path=str(root/'自动保存.reimbatch');ui.batch_password='AutosaveTest_123';ui.run_autosave();deadline=time.monotonic()+30
        while ui.autosave_busy and time.monotonic()<deadline:ui.update();time.sleep(.03)
        check(not ui.autosave_busy and batchfile.is_encrypted(ui.batch_path),'自动保存保留当前批次的密码加密设置')
        ui.settings['autosave_minutes']=0;ui.schedule_autosave()
        original_ask=app.messagebox.askyesnocancel;app.messagebox.askyesnocancel=lambda *a,**kw:None
        try:ui.close();check(ui.winfo_exists(),'关闭时取消保存提示会保留编辑窗口')
        finally:app.messagebox.askyesnocancel=original_ask
        ui.language='en';ui.localize_tick();check(ui.nav.heading('#0','text')=='' and ui.kind_choice.get()==ui.kind,'英文界面不改变内部类型值或项目数据')
        from preferences import tr
        check(tr('保存批次','en')=='Save batch' and tr('保存批次','zh')=='保存批次','中文英文基础界面文本可以切换')
        ui.language='zh';ui.localize_tick()
        second=D.project('颜色项目乙');second['entries']=[D.entry('调研交通','差旅报销')];second['entries'][0]['invoices']=[travel];D.sync(second)
        inventory=root/'批次详细清单.xlsx';D.inventory_table(ui.projects+[second],inventory,ui.batch['name'],ui.projects+[second])
        with zipfile.ZipFile(inventory) as z:
            sheet=z.read('xl/worksheets/sheet1.xml').decode();styles=z.read('xl/styles.xml').decode()
            check('s="3"' in sheet and 's="4"' in sheet and '1F4E78' in styles,'不同项目使用不同颜色标题分区')
            check('缺失' in sheet and '已有' in sheet and '批次合计' in sheet,'详细清单列出已有材料、缺失材料、单票金额及批次合计')
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        import threading
        captured=[]
        class MockAI(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));captured.append((self.path,body))
                payload={'content':[{'type':'text','text':'{"message":"test","actions":[]}'}]} if self.path.endswith('/messages') else {'choices':[{'message':{'content':'{"message":"test","actions":[]}'}}]}
                raw=json.dumps(payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
        server=ThreadingHTTPServer(('127.0.0.1',0),MockAI);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            config=dict(base_url=f'http://127.0.0.1:{server.server_address[1]}/v1',key='FAKE_TEST_KEY',model='mock-model',protocol='openai')
            result=ai_control.model_request(config,'仅检查项目',ui.public_state());check(json.loads(result)['actions']==[] and captured[-1][0].endswith('/chat/completions'),'OpenAI兼容协议请求在本机模拟服务中可解析')
            config['protocol']='anthropic';result=ai_control.model_request(config,'仅检查项目',ui.public_state());check(json.loads(result)['actions']==[] and captured[-1][0].endswith('/messages'),'Claude Messages协议请求在本机模拟服务中可解析')
            check(not any('FAKE_TEST_KEY' in json.dumps(body) for _,body in captured),'AI Key只放请求鉴权头，不混入项目提示正文')
        finally:server.shutdown();server.server_close()
        # Invisible layout measurement does not send input to the user's desktop.
        ui.attributes('-alpha',0);ui.deiconify();ui.geometry('1240x810');ui.update()
        check(ui.split.winfo_width()>1000 and ui.nav.winfo_width()>150,'常驻项目树在常见窗口尺寸下有独立可用宽度')
        ui.show_overview();ui.update();key=next(iter(ui.overview_rows));ui.overview_table.see(key);ui.update();box=ui.overview_table.bbox(key,'name')
        ui.overview_double(SimpleNamespace(x=box[0]+10,y=box[1]+10));check(ui.overview_editor is not None,'双击总览表格单元格出现真实的行内编辑框')
        edited_entry=ui.overview_rows[key][0];ui.overview_editor.delete(0,'end');ui.overview_editor.insert(0,'行内编辑实测');ui.commit_overview_editor();check(edited_entry['name']=='行内编辑实测','表格行内编辑保存回真实条目数据')
        check(ui.overview_table.winfo_height()>150 and ui.overview_table.winfo_width()>500,'统一表格在常见窗口尺寸下保留可用编辑面积')
        ui.geometry('1100x740');ui.show_entry_workspace();ui.update()
        for tab in range(3):
            ui.tabs.select(tab);ui.update()
            bottom=ui.entry_generate.winfo_rooty()+ui.entry_generate.winfo_height()
            check(ui.entry_generate.winfo_ismapped() and bottom<=ui.workspace.winfo_rooty()+ui.workspace.winfo_height() and ui.tabs.winfo_height()>100,f'最小窗口第{tab+1}页保留底部生成按钮及材料编辑面积')
        ui.show_overview();ui.update();ui.overview_table.see(key);ui.update()
        box=ui.overview_table.bbox(key,'notes');check(box and box[0]+box[2]<=ui.overview_table.winfo_width(),'最小窗口统一表格用途列在可视范围内，无默认横向溢出')
        check(ui.overview_generate.winfo_rooty()+ui.overview_generate.winfo_height()<=ui.overview.winfo_rooty()+ui.overview.winfo_height(),'最小窗口总览底部操作完整可见')
        ui.entry_id=edited_entry['id'];ui.bind_project();ui.show_entry_workspace();ui.update()
        check(str(ui.tree.column('amount','anchor'))=='e' and str(ui.overview_table.column('amount','anchor'))=='e','两个工作区的金额均右对齐')
        ui.attach_photo_paths(0,[str(sample_photo)]);check(bool(ui._photo_images),'配图页生成真实图片缩略图')
        ui.file_saved_digest=ui.audit_previous[0];ui.batch_path=str(root/'视觉保存状态.reimbatch');ui.update_file_state();check('已保存' in ui.file_state.get(),'批次文件保存状态区显示已保存')
        ui.entry_notes_var.set('新的未保存修改');ui.update_file_state();check('未保存' in ui.file_state.get(),'条目尚未写入批次文件的修改有明确提示')
        check(ui.nav_side.winfo_width()>=220,'初始项目树保留独立宽度，新建按钮不被主工作区挤压')
        from overview import display_amount
        check(display_amount('bad')=='待核对' and display_amount('12.3')=='12.30','金额无法识别时不伪显示为零，有效金额统一两位小数')

        from material_regression import run_material_checks
        run_material_checks(ui,root,inv,check,pdf)
        ui.withdraw()
    finally:ui.destroy()
    # A maximum-row, multiphoto document is included for independent Word rendering.
    photo=root/'实物.png';legacy.Image.new('RGB',(600,350),'#496b80').save(photo)
    doc_inv=inv('4000',count=15);doc_inv['photos']=[str(photo)]
    batch=dict(invoices=[doc_inv],amount=Decimal('4000'),count=15,category='采购');legacy.build_doc(batch,root/'15项配图验收单.docx')
    legacy.build_doc(dict(batch,invoices=[dict(doc_inv,photos=[])]),root/'15项无图验收单.docx')
    check(len(legacy.Document(root/'15项无图验收单.docx').inline_shapes)==0,'最终无图验收单没有图像占位')
    photo_doc=legacy.Document(root/'15项配图验收单.docx')
    heading=next(r for r in photo_doc.tables[0].rows if legacy.unique_cells(r)[0].text=='验收照片')
    check(all(p.paragraph_format.keep_with_next for p in legacy.unique_cells(heading)[0].paragraphs),'验收照片标题跟随第一张图片分页')
    disguised=root/'扩展名为jpg的WebP.jpg';legacy.Image.new('RGB',(120,80),'#38714b').save(disguised,format='WEBP');digest=hashlib.sha256(disguised.read_bytes()).hexdigest()
    sample_inv=inv('100');sample_inv['photos']=[str(disguised)];sample_batch=dict(invoices=[sample_inv],amount=Decimal('100'),count=1,category='采购')
    legacy.build_doc(sample_batch,root/'兼容图片验收单.docx')
    check(len(legacy.Document(root/'兼容图片验收单.docx').inline_shapes)==1 and hashlib.sha256(disguised.read_bytes()).hexdigest()==digest,'可读取但Word不直接支持的图片标准化嵌入，原图不变')
    rotated=root/'手机方向.jpg';exif=legacy.Image.Exif();exif[274]=6;legacy.Image.new('RGB',(120,80),'#38714b').save(rotated,exif=exif)
    sample_inv['photos']=[str(rotated)];legacy.build_doc(sample_batch,root/'手机方向验收单.docx');shape=legacy.Document(root/'手机方向验收单.docx').inline_shapes[0]
    check(shape.height>shape.width,'手机照片按EXIF方向嵌入，竖向照片不横倒或拉伸')
    sample_inv['photos']=[str(disguised)]*15;many=root/'15张图片验收单.docx';legacy.build_doc(sample_batch,many);drawing_ids=[]
    with zipfile.ZipFile(many) as packed:
        for name in packed.namelist():
            if name.startswith('word/') and name.endswith('.xml'):
                drawing_ids.extend(e.attrib['id'] for e in ET.fromstring(packed.read(name)).iter('{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr'))
    check(len(legacy.Document(many).inline_shapes)==15 and len(drawing_ids)==len(set(drawing_ids)),'15图文档与模板页眉中的绘图ID全局唯一，避免Word报损坏')
    grids=[g for row in legacy.Document(many).tables[0].rows for cell in legacy.unique_cells(row) for g in cell.tables]
    check([len(g.rows[0].cells) for g in grids]==[4,4,4,3],'15张图片按4加4加4加3紧密分行，尾行不生成空白图片格')
    shapes=legacy.Document(many).inline_shapes
    check(all(s.width<=legacy.Inches(1.28)+2 and s.height<=legacy.Inches(1.25)+2 for s in shapes),'网格图片在单元格限宽限高内按比例缩放')
    layouts=[]
    for count in [1,4,5]:
        sample_inv['photos']=[str(disguised)]*count;out=root/f'网格{count}图.docx';legacy.build_doc(sample_batch,out)
        grids=[g for row in legacy.Document(out).tables[0].rows for cell in legacy.unique_cells(row) for g in cell.tables]
        layouts.append([len(g.rows[0].cells) for g in grids])
    check(layouts==[[1],[4],[4,1]],'单图四图五图保持最多每排四张且不补空格')
    def row_extract(label,lines):
        path=root/(label+'.pdf');document=legacy.pymupdf.open();page=document.new_page()
        page.insert_text((30,30),'发票号码：12345678901234567890 深圳科创学院 （小写）￥10.90',fontname='china-s')
        for n,line in enumerate(lines):page.insert_text((30,70+n*24),line,fontsize=10)
        document.save(path);document.close();return app.extract(path)
    no_unit=row_extract('空单位',['*Goods*Part 1 5.1683168316832 5.17 1% 0.05'])
    check(no_unit['items'][0]['qty']=='1' and no_unit['items'][0]['amount']=='5.22','单位为空时仍读取票面明确数量和含税金额')
    discount=row_extract('折扣',['*Goods*Part pcs 1 14.6 14.60 13% 1.90','*Goods*Part -4.96 13% -0.64'])
    check(discount['items'][0]['amount']=='10.90' and len(discount['items'])==1,'相邻匹配折扣行的金额和税额归入原项目')
    mismatch=row_extract('折扣不匹配',['*Goods*Part pcs 1 14.6 14.60 13% 1.90','*Other*Part -4.96 13% -0.64'])
    check(mismatch['items'][0]['amount']=='16.50','不相关折扣不能扣减上一物品金额，保留金额不符待核对')
    missing=row_extract('数量空白',['*Goods*Part 17.61 13% 2.29'])
    check(not missing['items'][0]['qty'],'票面没有数量时不擅自填为一件或一批')
    excessive=row_extract('折扣超过原价',['*Goods*Part pcs 1 14.6 14.60 13% 1.90','*Goods*Part -20.00 13% -2.60'])
    check(excessive['items'][0]['amount']=='16.50','超原价折扣不自动归入物品，留待核对')
    repeated=row_extract('多行对应折扣',['*Goods*Part pcs 2 50 100.00 13% 13.00','*Goods*Part -10.00 13% -1.30','*Goods*Part pcs 1 50 50.00 13% 6.50','*Goods*Part -5.00 13% -0.65'])
    check([i['amount'] for i in repeated['items']]==['101.70','50.85'],'重复同名商品的折扣分别归入各自紧邻的明细')
    (root/'测试报告.json').write_text(json.dumps(dict(passed=len(results),tests=results,materials='模拟材料；不代表所有真实发票版式均已覆盖'),ensure_ascii=False,indent=2),encoding='utf-8')
