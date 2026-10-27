import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog
import json,hashlib,copy,threading,queue,ctypes,math
from pathlib import Path
from datetime import datetime
import batchfile,domain as D

EN={'报销项目助手':'Reimbursement Assistant','项目 / 报销项 / 资料':'Projects / Items / Files','报销项目':'Project','新建':'New','重命名':'Rename','报销类型':'Type','新建报销项':'New item','回收站':'Recycle bin','新建批次':'New batch','保存批次':'Save batch','显示隐藏项':'Show hidden items','附件 / 签字验收单':'Attachments / signed forms','检查当前项目':'Check project','手动完成 / 撤销':'Complete / undo','检查全部项目':'Check all','归档全部待报销材料':'Archive batch','AI / 操作接口':'AI / API','导入发票':'Import invoices','导入文件夹':'Import folder','核对 / 配图':'Review / photos','查看原票':'Open invoice','移除':'Remove','保存项目':'Save batch','打开项目':'Open batch','金额清单':'Amount list','分组导出':'Generate forms','设置 / Settings':'Settings','导出文件清单':'Export inventory','显示父子关系（箭头）':'Show parent-child arrows','打开文件':'Open file','新建报销项目':'New project','保存整个批次':'Save entire batch','重命名批次':'Rename batch','修改报销项名称':'Rename item','取消标红':'Remove red mark','标红':'Mark red','取消隐藏':'Unhide','隐藏':'Hide','删除项目':'Delete project','删除报销项':'Delete item','项目库':'Batch library','此节点没有子节点':'This node has no children','恢复所选记录':'Restore selected','发票':'Invoice','配图':'Photos','签字验收单':'Signed acceptance form','发票文件':'Invoice file','发票号码':'Invoice number','含税金额（元）':'Amount (tax included)','项目数':'Lines','图片':'Photos','待办与提醒':'Status / issues','未上传':'Not attached','添加附件':'Add files','清除关联':'Remove links','打开附件文件夹':'Open attachment folder','零星采购':'Small purchases','服务采购':'Service procurement','物资采购':'Material procurement','差旅报销':'Travel expenses','发票整理  /  金额清单  /  采购验收':'Invoices / Amounts / Acceptance','把发票文件或整个文件夹拖到这里，即可导入':'Drop invoice files or folders here','支持多选拖入 · 自动读取子文件夹 · 也可拖到下方发票列表或窗口空白处':'Multiple files and subfolders supported; drop on the list or blank area','请在左侧新建有名称的报销项':'Create a named item in the left pane','自动检查结果':'Check results','添加本票图片（可多选）':'Add photos (multiple)','不配图 / 清除图片':'No photos / clear','新增项目':'Add line','编辑项目':'Edit line','删除项目':'Delete line','保存核对结果':'Save review','保存并下一张':'Save and next','物品名称':'Item name','规格型号':'Model / specification','数量':'Quantity','含税金额':'Tax-inclusive amount','保存项目':'Save batch','购买方':'Buyer','整票含税金额':'Invoice total','费用/物品类别':'Expense category','销售方名称':'Supplier name','销售方税号':'Supplier tax ID','开票日期 YYYY-MM-DD':'Invoice date YYYY-MM-DD','差旅费用说明（可选）':'Travel description (optional)','品名':'Description','型号':'Model','含税小计':'Line total','保存AI配置':'Save AI settings','服务商':'Provider','模型ID（自行填写）':'Model ID','启动 / 停止接口':'Start / stop API','复制本机访问令牌':'Copy local API token','发送给AI生成计划':'Ask AI for a plan','执行已查看的计划':'Apply reviewed plan','本机API未启动':'Local API is stopped','允许外部AI修改（包括可恢复删除）':'Allow external AI edits (reversible deletion)','报销项目助手 · 4.0':'Reimbursement Assistant 4.0','导入提示':'Import notice','文件无法打开':'Cannot open file','保存失败':'Save failed','保存并退出':'Save and exit','保存批次工作':'Save batch work','是否保存当前报销批次后退出？\n“是”保存，“否”不另存直接退出，“取消”继续编辑。':'Save this reimbursement batch before exiting?\nYes: save, No: exit without a new save, Cancel: keep editing.','保存后关闭':'Save before closing'}
EN.update({'发票尚未核对确认':'Invoice not reviewed','请补充销售方名称或税号':'Enter supplier name or tax ID','请补充发票号码':'Enter invoice number','原发票缺失、为空或不可读取':'Invoice file is missing, empty or unreadable','项目没有发票':'No invoices in this project','发票核对通过':'Invoice reviewed','保存批次工作':'Save batch work','核对发票与资料':'Review invoice and materials','批次加密 / Batch encryption':'Batch encryption','创建报销项':'Create item','选择报销项类型':'Choose item type','设置无效 / Invalid settings':'Invalid settings','零星采购报销':'Small purchase reimbursement'})
EN.update({'新建报销项':'New reimbursement item','填写报销项名称（例如：传感器采购、深圳调研交通）：':'Name the reimbursement item (for example, sensors or Shenzhen fieldwork travel):','报销项名称：':'Item name:','项目名称：':'Project name:','批次名称：':'Batch name:','报销批次文件':'Reimbursement batch','项目库':'Project library','没有发票':'No invoices','请选择报销项':'Select an item','请先选择报销项':'Select an item first','请先新建报销项':'Create a named item first','请在左侧新建或选择一个报销项。':'Create or select a named item in the left pane.','请在左侧新建并填写报销项名称，再导入或拖入发票。':'Create and name an item in the left pane before importing invoices.','删除确认':'Confirm deletion','未找到回收记录':'Deleted record not found','导出金额清单失败':'Amount list export failed','金额须为非负数，最多两位小数':'Enter a non-negative amount with at most two decimal places.','请填写真实采购项目':'Enter the actual purchase lines.','逐项含税金额之和与整票金额不一致':'The sum of line amounts does not match the invoice total.','请核对并确认识别结果':'Review and confirm the extracted invoice data.','请填写发票号码':'Enter the invoice number.','单票超过5000元，不自动拆票':'Invoice exceeds 5,000. It will not be split automatically.','零星采购单票超过1000元':'Small-purchase invoice exceeds 1,000.','单票采购项目超过15项，不自动拆票':'Invoice has more than 15 lines. It will not be split automatically.','每行一个采购项目，小计填含税金额。每张发票可选一张或多张图片；直接下一张表示不配图，不留图片空档。':'Enter actual purchase lines and tax-inclusive amounts. Photos are optional; skipping them creates no blank photo slots.','我已核对票号、金额、销售方、日期与当前报销类型；采购明细与整票金额一致，差旅可不录采购明细。':'I reviewed the invoice number, amount, supplier, date and reimbursement type. Purchase lines reconcile; travel need not have purchase lines.','识别原文（供核对；无法可靠识别的字段留空，不自动编造）':'Extracted text for review. Unreliable fields are left blank.','每张发票可选一张或多张图片':'Each invoice may have one or more optional photos.'})
EN.update({'报销项':'Expense group','新建报销项':'New expense group','报销条目':'Expense entry','新建报销条目':'New expense entry','创建报销条目':'Create expense entry','选择报销条目类型':'Select expense entry type','报销项 / 报销条目 / 资料':'Groups / Entries / Files','修改报销条目名称':'Rename expense entry','报销条目名称：':'Expense entry name:','报销项名称：':'Expense group name:','删除报销条目':'Delete expense entry','请先新建报销条目':'Create an expense entry first','请在左侧新建并填写报销条目名称，再导入或拖入发票。':'Create and name an expense entry in the left pane before importing invoices.','填写报销条目名称（例如：传感器采购、深圳调研交通）：':'Name the expense entry (for example, sensors or fieldwork travel):','请在左侧新建有名称的报销条目':'Create a named expense entry in the left pane'})
EN.update({'当前报销项':'Expense group','修改报销项名称':'Rename expense group','类型':'Type','选中报销条目后，在这里修改内容':'Edit the selected expense entry here','条目名称':'Entry name','保存条目修改':'Save entry changes','说明 / 用途':'Notes / purpose','发票与内容修改':'Invoices / edit contents','发票配图':'Invoice photos','其他附件 / 签字件':'Attachments / signed forms','核对 / 修改发票内容':'Review / edit invoice','为选中发票添加图片':'Add photos to invoice','移除发票':'Remove invoice','对应发票':'Invoice','添加图片（可多选）':'Add photos','打开图片':'Open photo','移除图片':'Remove photo','明细数':'Lines','核对状态':'Review status','材料类别':'Material category','文件 / 状态':'File / status','移除关联':'Remove link','检查报销项':'Check group','生成验收单 / 差旅表':'Generate forms','归档整个批次':'Archive batch','编辑报销条目 / 添加材料':'Edit entry / add files','新建报销项：先选类型，再填名称':'New expense group: type, then name','① 请选择报销类型':'1. Select the reimbursement type','② 再填写报销项名称':'2. Enter the expense group name','创建报销项':'Create expense group'})
EN.update({'＋ 新建报销条目':'＋ New entry','编辑选中条目':'Edit selected entry','报销条目 · 双击修改':'Entry · double-click to edit','企业名称 · 双击修改':'Company · double-click to edit','发票 · 点击上传':'Invoice · click to upload','金额（元）':'Amount (CNY)','配图 · 点击添加':'Photos · click to add','附件 · 点击上传':'Files · click to upload','用途 · 双击修改':'Purpose · double-click to edit','上传条目附件':'Upload entry files','选择文件并上传':'Select files and upload','每张发票占一行；同一条目的名称和用途保持同步。点击发票、配图或附件列可直接上传；双击金额可核对发票。':'One invoice per row. Entry names and purposes stay synchronized. Click invoice, photo or attachment cells to upload. Double-click an amount to review.'})
EN.update({'工作目录':'Workspace','设置':'Settings','批次与工具':'Batch and tools','修改记录':'History','取消':'Cancel','返回报销项总览':'Back to group','生成本报销项表单':'Generate group forms','更多操作':'More actions','输出范围：当前报销项；归档为整个批次':'Forms: current group · Archive: whole batch','查看报销规则':'View rules','报销规则':'Reimbursement rules','关闭':'Close','标记完成 / 撤销':'Complete / undo','检查全部报销项':'Check all groups','从一张发票开始':'Start with an invoice','支持拖入 PDF、图片或整个文件夹。识别后请核对金额与销售方。':'Drop PDFs, images or a folder here. Review the extracted amount and supplier.','双击发票核对内容；可拖入文件或文件夹。':'Double-click an invoice to review. Files and folders can be dropped here.','图片为可选材料':'Photos are optional','先导入发票，再选择对应发票添加图片；支持一张或多张。':'Import an invoice first, then add one or more photos.','不配图不会在最终验收单中留下图片空档。差旅报销无需配图。':'No blank photo slots in the final form. Travel needs no photos.','预览':'Preview','签字件按验收单编号关联；必需和可选材料分别显示。':'Link signed copies to their form number. Required and optional files are listed separately.','建立第一个报销条目':'Create the first entry','每个条目归集对应发票、图片和附件；同一报销项下可统一整理。':'Each entry keeps its invoices, photos and files together. Manage all entries in this group here.','双击名称、企业或用途可编辑；点击发票、配图或附件可添加材料；双击金额可核对。':'Double-click a name, company or purpose to edit. Click invoice, photos or files to add. Double-click amounts to review.','发票 / 添加':'Invoice / add','金额（元）':'Amount (CNY)','配图':'Photos','附件':'Files','用途':'Purpose','需补充':'Required · missing','未添加（可选）':'Not added · optional','保存设置':'Save settings','保存条目修改':'Update entry'})
EN.update({'反选':'Invert selection','全选':'Select all','取消全选':'Clear selection','文件夹':'Folder','可拖入 · Ctrl / Shift 多选':'Drop files · Ctrl / Shift to select','移除所选发票':'Remove selected invoices','移除所选图片':'Remove selected photos','移除所选附件':'Remove selected files','选择图片文件夹':'Select photo folder','选择附件文件夹':'Select attachment folder','导入拖入的附件':'Import dropped files','选择图片（支持多选、Ctrl+A全选）':'Select photos (multiple, Ctrl+A for all)','选择附件（支持多选、Ctrl+A全选）':'Select files (multiple, Ctrl+A for all)'})
EN.update({'导入材料':'Import materials','选择发票（可多选）':'Select invoices (multiple)','选择发票文件夹':'Select invoice folder','核对所选发票':'Review selected invoices','打开所选原始发票':'Open selected invoice files','选择图片（可多选）':'Select photos (multiple)','打开所选图片':'Open selected photos','选择附件（可多选）':'Select files (multiple)','切换附件类别':'Choose file category','打开所选附件':'Open selected files','移除所选关联':'Remove selected links','选择操作':'Selection','编辑该报销条目':'Edit this entry','上传材料':'Upload materials','上传发票':'Upload invoices','上传配图':'Upload photos','上传附件':'Upload files'})
for k,value in D.RULES.items():
    EN[value]={'零星采购':'Same supplier/calendar month total <= 1,000; per form <= 5,000 and 15 lines. Required: invoices + signed form.','服务采购':'One invoice per form, <= 5,000 and 15 lines. Required: service request + signed form.','物资采购':'Invoice/form <= 5,000 and 15 lines. Required: purchase request/approval, receipt record and signed form.','差旅报销':'No amount or line limit. No photos/acceptance form. Required: invoices, itinerary, travel and research requests.'}[k]
def tr(value,lang):
    if lang!='en':return value
    if value in EN:return EN[value]
    replacements=[('已识别金额合计','Recognized total'),('报销项：','Item: '),('批次：','Batch: '),('项目合计','Project total'),('手动：','Manual: '),('自动检查：','Check: '),('已完成','Completed'),('整理中','In progress'),('待处理','Issues: '),('通过','Passed'),('已识别金额','Amounts recognized'),('金额待识别','Amounts missing'),('超1000元','Over 1,000'),('共 ','Total '),('张发票',' invoices'),('张',' invoices'),('项',' items'),('票',' invoices'),('发票核对通过','Invoice reviewed'),('不配图','No photos'),('待识别','Unrecognized')]
    text=value
    for a,b in replacements:text=text.replace(a,b)
    return text

class PreferencesMixin:
    def pre_preferences(self):
        self.settings=dict(language='zh',autosave_minutes=5);self.history=[];self.batch_path=None;self.batch_password=None;self.audit_previous=None;self.autosave_results=queue.Queue();self.autosave_busy=False;self.autosave_timer=None
        path=self.data_dir/'界面设置.json'
        if path.exists():
            try:self.settings.update(json.loads(path.read_text(encoding='utf-8')))
            except Exception:pass
        self.language=self.settings.get('language','zh')
    def post_preferences(self,prompt=True):
        ttk.Button(self.nav_bottom,text='设置',command=self.settings_panel).pack(fill='x',pady=(6,0))
        if prompt:self.choose_language()
        self.after(150,self.localize_tick);self.schedule_autosave();self.after(300,self.check_autosave)
        if prompt:self.install_shutdown_hook()
        get=self.kind_choice.get;set_value=self.kind_choice.set;reverse={EN[k]:k for k in D.KINDS}
        self.kind_choice.get=lambda:reverse.get(get(),get())
        self.kind_choice.set=lambda value:set_value(EN.get(value,value) if self.language=='en' else reverse.get(value,value))
        # Translate standard dialog chrome at invocation; user-entered names remain unchanged.
        for module,names in [(messagebox,['showinfo','showerror','showwarning','askyesno','askyesnocancel','askokcancel']),(simpledialog,['askstring']),(filedialog,['askopenfilename','askopenfilenames','askdirectory','asksaveasfilename'])]:
            for name in names:
                current=getattr(module,name);original=getattr(current,'_original_dialog',current)
                def wrap(*args,_fn=original,**kw):
                    args=tuple(tr(a,self.language) if isinstance(a,str) else a for a in args)
                    for key in ['title','message','prompt']:
                        if key in kw and isinstance(kw[key],str):kw[key]=tr(kw[key],self.language)
                    return _fn(*args,**kw)
                wrap._original_dialog=original;setattr(module,name,wrap)
    def choose_language(self):
        win=tk.Toplevel(self);win.title('选择语言 / Choose language');win.geometry('420x220');win.grab_set();self.polish_dialog(win)
        ttk.Label(win,text='请选择本次界面语言\nChoose the interface language').pack(pady=20)
        def choose(lang):self.language=lang;self.settings['language']=lang;self.save_settings();win.destroy()
        row=ttk.Frame(win);row.pack();ttk.Button(row,text='中文',style='Primary.TButton',command=lambda:choose('zh')).pack(side='left',padx=10);ttk.Button(row,text='English',command=lambda:choose('en')).pack(side='left',padx=10)
        win.protocol('WM_DELETE_WINDOW',lambda:choose(self.language));self.wait_window(win)
    def save_settings(self):(self.data_dir/'界面设置.json').write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8')
    def localize_tick(self):
        try:
            self.localize_widget(self)
            for name in ['rule','total_text','count_text','project_status','entry_label','status']:
                var=getattr(self,name,None)
                if not var:continue
                value=var.get();record=getattr(var,'_i18n_record',None)
                original=record[0] if record and value==record[1] else value;translated=tr(original,self.language)
                if value!=translated:var.set(translated)
                var._i18n_record=(original,translated)
            desired_values=tuple(EN[k] if self.language=='en' else k for k in D.KINDS)
            if tuple(self.kind_choice.cget('values'))!=desired_values:self.kind_choice.configure(values=desired_values)
            desired_value=EN.get(self.kind,self.kind) if self.language=='en' else self.kind
            if str(self.kind_choice.tk.call(self.kind_choice._w,'get'))!=desired_value:self.kind_choice.set(self.kind)
        except tk.TclError:return
        self.after(300,self.localize_tick)
    def localize_widget(self,w):
        if isinstance(w,tk.Toplevel):
            self.polish_dialog(w)
            title=w.title();previous=getattr(w,'_last_title',None)
            if title!=previous:w._original_title=title
            translated=tr(getattr(w,'_original_title',title),self.language)
            if title!=translated:w.title(translated)
            w._last_title=translated
        if isinstance(w,tk.Menu):
            try:
                count=w.index('end')
                if count is not None:
                    for n in range(count+1):
                        if w.type(n)!='separator':
                            label=w.entrycget(n,'label');translated=tr(label,self.language)
                            if label!=translated:w.entryconfigure(n,label=translated)
            except tk.TclError:pass
        if not isinstance(w,tk.Menu):
            try:
                text=str(w.cget('text'));prior=getattr(w,'_translated_text',None)
                if text!=prior:w._original_text=text
                original=getattr(w,'_original_text',text);translated=tr(original,self.language)
                if text!=translated:w.configure(text=translated)
                w._translated_text=translated
            except tk.TclError:pass
        if isinstance(w,ttk.Treeview) and w is not self.nav:
            for col in w['columns']:
                current=w.heading(col,'text');saved=getattr(w,'_heading_originals',{})
                if col not in saved:saved[col]=current
                w._heading_originals=saved;translated=tr(saved[col],self.language)
                if current!=translated:w.heading(col,text=translated)
            if w is self.tree:
                cache=getattr(w,'_row_originals',{})
                for iid in w.get_children():
                    values=list(w.item(iid,'values'))
                    if not values:continue
                    record=cache.get(iid);original=record[0] if record and values[-1]==record[1] else values[-1];translated=tr(original,self.language)
                    if values[-1]!=translated:values[-1]=translated;w.item(iid,values=values)
                    cache[iid]=(original,translated)
                w._row_originals=cache
        for child in w.winfo_children():self.localize_widget(child)
    def settings_panel(self):
        english=self.language=='en';win=tk.Toplevel(self);win.title('Settings' if english else '设置');win.geometry('500x350');win.grab_set();self.polish_dialog(win)
        body=ttk.Frame(win,padding=24);body.pack(fill='both',expand=True);ttk.Label(body,text='Settings' if english else '界面与自动保存',style='Title.TLabel').pack(anchor='w',pady=(0,18))
        row=ttk.Frame(body);row.pack(fill='x');ttk.Label(row,text='Language' if english else '界面语言').pack(side='left');lang=tk.StringVar(value='中文' if self.language=='zh' else 'English');ttk.Combobox(row,textvariable=lang,values=['中文','English'],state='readonly',width=18).pack(side='right')
        names=['Off','Every minute','Every 5 minutes','Every hour','Custom minutes'] if english else ['不自动保存','每1分钟','每5分钟','每1小时','自定义分钟数'];values=[0,1,5,60];minutes=float(self.settings['autosave_minutes']);selected=values.index(minutes) if minutes in values else 4
        row=ttk.Frame(body);row.pack(fill='x',pady=(16,0));ttk.Label(row,text='Auto-save' if english else '自动保存').pack(side='left');choice=ttk.Combobox(row,values=names,state='readonly',width=18);choice.current(selected);choice.pack(side='right')
        custom=tk.StringVar(value=str(minutes if minutes else 5));row=ttk.Frame(body);row.pack(fill='x',pady=(10,0));ttk.Label(row,text='Minutes' if english else '自定义（分钟）').pack(side='left');custom_input=ttk.Entry(row,textvariable=custom,width=20);custom_input.pack(side='right')
        def mode(event=None):custom_input.configure(state='normal' if choice.current()==4 else 'disabled')
        choice.bind('<<ComboboxSelected>>',mode);mode()
        def save():
            try:
                minutes=float(custom.get()) if choice.current()==4 else values[choice.current()]
                if not math.isfinite(minutes) or minutes<0 or minutes>43200:raise ValueError('0–43200 minutes')
                self.language='zh' if lang.get()=='中文' else 'en';self.settings.update(language=self.language,autosave_minutes=minutes);self.save_settings();self.schedule_autosave();self.refresh();self.localize_widget(self);self.update_file_state();win.destroy()
            except Exception as e:messagebox.showerror('Invalid settings' if english else '设置无效',str(e),parent=win)
        bar=ttk.Frame(body);bar.pack(side='bottom',fill='x');ttk.Button(bar,text='Save' if english else '保存设置',style='Primary.TButton',command=save).pack(side='right');ttk.Button(bar,text='Cancel' if english else '取消',command=win.destroy).pack(side='right',padx=8)
    def schedule_autosave(self):
        if self.autosave_timer:
            try:self.after_cancel(self.autosave_timer)
            except tk.TclError:pass
        minutes=float(self.settings.get('autosave_minutes',5));self.autosave_timer=self.after(max(1000,int(minutes*60000)),self.run_autosave) if minutes>0 else None
    def run_autosave(self):
        if not self.importing and not self.autosave_busy:
            folder=self.data_dir/'自动保存批次';folder.mkdir(exist_ok=True);path=Path(self.batch_path) if self.batch_path else folder/(self.batch['id']+batchfile.EXT)
            self.autosave_digest=self.audit_previous[0] if self.audit_previous else None
            data=copy.deepcopy((self.batch,self.projects,getattr(self,'deleted_records',[]),self.history));password=self.batch_password;self.autosave_busy=True
            def worker():
                try:batchfile.save_batch(path,data[0],data[1],data[2],password=password,history=data[3]);self.autosave_results.put((True,str(path)))
                except Exception as e:self.autosave_results.put((False,str(e)))
            threading.Thread(target=worker,daemon=True).start()
        self.schedule_autosave()
    def check_autosave(self):
        try:
            while True:
                ok,text=self.autosave_results.get_nowait();self.autosave_busy=False
                if ok and self.batch_path and Path(text)==Path(self.batch_path):self.file_saved_digest=getattr(self,'autosave_digest',None)
                self.status.set(('Auto-saved: ' if self.language=='en' else '已自动保存：')+text if ok else ('Auto-save failed: ' if self.language=='en' else '自动保存失败：')+text)
        except queue.Empty:pass
        self.after(300,self.check_autosave)
    def record_history(self):
        data=json.loads(json.dumps(dict(batch=self.batch,projects=self.projects,deleted_records=getattr(self,'deleted_records',[])),ensure_ascii=False));encoded=json.dumps(data,ensure_ascii=False,sort_keys=True);digest=hashlib.sha256(encoded.encode()).hexdigest()
        if self.audit_previous and self.audit_previous[0]!=digest:
            changes=[]
            def diff(old,new,path=''):
                if len(changes)>=100:return
                if type(old)!=type(new):changes.append(dict(path=path,before=str(old)[:250],after=str(new)[:250]));return
                if isinstance(old,dict):
                    for key in old.keys()|new.keys():diff(old.get(key),new.get(key),path+'/'+str(key))
                elif isinstance(old,list):
                    if len(old)!=len(new):changes.append(dict(path=path,description=f'数量 {len(old)} → {len(new)}'))
                    for i,(a,b) in enumerate(zip(old,new)):diff(a,b,path+'/'+str(i))
                elif old!=new:changes.append(dict(path=path,before=old,after=new))
            diff(self.audit_previous[1],data);self.history.append(dict(time=datetime.now().astimezone().isoformat(),previous=self.audit_previous[0],current=digest,changes=changes))
        self.audit_previous=(digest,data)
        self.update_file_state()
    def encryption_choice(self):
        win=tk.Toplevel(self);win.title('批次加密 / Batch encryption');win.geometry('460x280');win.grab_set();result=[]
        encrypted=tk.BooleanVar(value=bool(self.batch_password));ttk.Checkbutton(win,text='密码加密此批次 / Encrypt with password',variable=encrypted).pack(pady=18)
        password=tk.StringVar(value=self.batch_password or '');confirm=tk.StringVar(value=self.batch_password or '')
        ttk.Label(win,text='密码 / Password（至少8位 / min 8 characters）').pack();ttk.Entry(win,textvariable=password,show='•',width=35).pack();ttk.Label(win,text='确认密码 / Confirm password').pack(pady=(10,0));ttk.Entry(win,textvariable=confirm,show='•',width=35).pack()
        ttk.Label(win,text='请保管密码，遗失无法恢复 / Keep the password; it cannot be recovered.').pack(pady=6)
        def save():
            if encrypted.get() and (len(password.get())<8 or password.get()!=confirm.get()):messagebox.showerror('密码 / Password','密码至少8位且两次输入一致 / Use matching passwords, min 8 characters');return
            result.append(password.get() if encrypted.get() else None);win.destroy()
        ttk.Button(win,text='保存 / Save',command=save).pack(pady=18);self.wait_window(win);return result
    def view_history(self):
        win=tk.Toplevel(self);win.title('修改记录 / Change history');win.geometry('900x600');txt=tk.Text(win,wrap='word');txt.pack(fill='both',expand=True,padx=12,pady=12);txt.insert('1.0',json.dumps(self.history,ensure_ascii=False,indent=2));txt.configure(state='disabled')
    def export_inventory(self):
        win=tk.Toplevel(self);win.title('导出文件清单 / Export inventory');win.geometry('500x250');scope=tk.StringVar(value='selected');ttk.Radiobutton(win,text='选中的项目或报销项 / Selected project or item',variable=scope,value='selected').pack(anchor='w',padx=20,pady=16);ttk.Radiobutton(win,text='整个报销批次 / Entire batch',variable=scope,value='all').pack(anchor='w',padx=20)
        def save():
            projects=self.projects
            if scope.get()=='selected':
                node=self.nodes.get(self.nav.selection()[0],{}) if self.nav.selection() else {}
                p=node.get('project',self.current());e=node.get('entry') or (node.get('obj') if node.get('type')=='entry' else None);projects=[copy.deepcopy(p)]
                if node.get('type')=='batch':projects=self.projects
                if e:projects[0]['entries']=[copy.deepcopy(e)];D.sync(projects[0])
            path=filedialog.asksaveasfilename(parent=win,defaultextension='.xlsx',filetypes=[('Excel workbook','*.xlsx')])
            if path:D.inventory_table(projects,path,self.batch['name'],self.projects);self.status.set('已导出 / Exported: '+path);win.destroy()
        ttk.Button(win,text='导出 / Export',command=save).pack(pady=24)
    def install_shutdown_hook(self):
        # Ask before Windows closes the application during shutdown/logoff.
        try:
            user32=ctypes.windll.user32;getroot=user32.GetAncestor;getroot.argtypes=[ctypes.c_void_p,ctypes.c_uint];getroot.restype=ctypes.c_void_p;hwnd=getroot(self.winfo_id(),2)
            pointer=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t)
            setter=user32.SetWindowLongPtrW;setter.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];setter.restype=ctypes.c_void_p
            call=user32.CallWindowProcW;call.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t];call.restype=ctypes.c_ssize_t
            def procedure(window,msg,wparam,lparam):
                if msg==0x0011:
                    try:self.close();return 1 if not self.winfo_exists() else 0
                    except tk.TclError:return 1
                    except Exception:return 0
                return call(self._old_wndproc,window,msg,wparam,lparam)
            self._wndproc_callback=pointer(procedure);self._old_wndproc=setter(hwnd,-4,self._wndproc_callback);self._hook_hwnd=hwnd
        except Exception:self._old_wndproc=None
    def destroy(self):
        if getattr(self,'_old_wndproc',None):
            setter=ctypes.windll.user32.SetWindowLongPtrW;setter.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];setter.restype=ctypes.c_void_p
            setter(self._hook_hwnd,-4,self._old_wndproc);self._old_wndproc=None
        return super().destroy()
