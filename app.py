import os,sys,json,re,uuid,traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
import legacy
import domain as D
from navigation import TreeMixin
from ai_control import AIMixin
import batchfile
from preferences import PreferencesMixin
from workspace import WorkspaceMixin

original_extract=legacy.extract
def extract(path):
    inv=original_extract(path);text=inv['text']
    date=re.search(r'(20\d{2})\s*[年/.-]\s*(\d{1,2})\s*[月/.-]\s*(\d{1,2})',text)
    inv['date']=''
    if date:
        try:inv['date']=datetime(*map(int,date.groups())).strftime('%Y-%m-%d')
        except ValueError:pass
    names=re.findall(r'名称\s*[:：]\s*([^\n]+)',text)
    inv['seller']=names[-1].strip() if names else ''
    taxes=re.findall(r'(?:纳税人识别号|统一社会信用代码)\s*[:：]\s*([A-Za-z0-9]{15,20})',text)
    inv['seller_tax']=taxes[-1] if taxes else '';inv['purpose']=''
    return inv
legacy.extract=extract

class App(TreeMixin,AIMixin,PreferencesMixin,WorkspaceMixin,legacy.App):
    def __init__(self,data_dir=None,prompt_language=True):
        self.ready=False;self.projects=[];self.index=0;self.kind=D.KINDS[0];self.entry_id=None;self.batch=dict(id=D.uid(),name='新报销批次')
        root=Path(data_dir or os.environ.get('REIMBURSE_DATA_DIR') or Path(os.environ.get('LOCALAPPDATA',Path.home()))/'报销项目助手')
        self.data_dir=root;root.mkdir(parents=True,exist_ok=True);self.state_file=root/'项目库.json'
        self.pre_preferences()
        startup_error=''
        if self.state_file.exists():
            try:self.projects=self.read_state(self.state_file)
            except Exception as e:startup_error='项目库未能读取，原文件保留，请使用“打开项目”恢复：'+str(e)
        if not self.projects:self.projects=[dict(D.project('请先新建报销项'),placeholder=True)]
        self.recovery=bool(startup_error)
        super().__init__();self.title('CounterMiao 4.3');self.geometry('1240x810');self.minsize(1100,740)
        widgets=self.winfo_children();header=widgets[0]
        for child in header.winfo_children():
            if isinstance(child,tk.Label) and child.cget('text')=='采购验收助手':child.configure(text='CounterMiao')
        try:
            from PIL import ImageTk
            icon=legacy.BASE/'CounterMiao.ico';logo=legacy.BASE/'CounterMiao.png';self.iconbitmap(str(icon))
            self._brand_image=ImageTk.PhotoImage(legacy.Image.open(logo).resize((44,44)));tk.Label(header,image=self._brand_image,bg='#185c37').pack(side='left',padx=4,before=header.winfo_children()[0])
        except (OSError,tk.TclError):pass
        controls=ttk.Frame(self);controls.pack(fill='x',padx=24,pady=10,before=widgets[1])
        ttk.Label(controls,text='报销项').pack(side='left')
        self.project_choice=ttk.Combobox(controls,state='readonly',width=24);self.project_choice.pack(side='left',padx=6)
        self.project_choice.bind('<<ComboboxSelected>>',self.switch_project)
        ttk.Button(controls,text='新建报销项',command=self.new_project).pack(side='left',padx=3)
        ttk.Button(controls,text='重命名',command=self.rename_project).pack(side='left',padx=3)
        ttk.Label(controls,text='报销类型').pack(side='left',padx=(20,4))
        self.kind_choice=ttk.Combobox(controls,state='readonly',values=D.KINDS,width=14);self.kind_choice.set(self.kind);self.kind_choice.pack(side='left');self.kind_choice.bind('<<ComboboxSelected>>',self.switch_kind)
        self.entry_label=tk.StringVar(value='请新建报销项');ttk.Label(controls,textvariable=self.entry_label,wraplength=230).pack(side='left',padx=8)
        second=ttk.Frame(self);second.pack(fill='x',padx=24,pady=(0,8),before=widgets[1])
        ttk.Button(second,text='附件 / 签字验收单',command=self.attachments).pack(side='left',padx=(0,8))
        ttk.Button(second,text='检查当前项目',command=self.check).pack(side='left',padx=3)
        ttk.Button(second,text='手动完成 / 撤销',command=self.complete).pack(side='left',padx=3)
        ttk.Button(second,text='检查全部项目',command=lambda:self.check(True)).pack(side='right',padx=5)
        ttk.Button(second,text='归档全部待报销材料',command=self.archive).pack(side='right',padx=5)
        ttk.Button(second,text='AI / 操作接口',command=self.ai_panel).pack(side='left',padx=5)
        self.project_status=tk.StringVar();ttk.Label(self,textvariable=self.project_status,foreground='#217346',wraplength=1150).pack(fill='x',padx=24,pady=(0,6),before=widgets[1])
        self.tree.configure(height=5)
        widgets[-1].pack(side='bottom',fill='x',before=widgets[1])
        self.rule=tk.StringVar(value=D.RULES[self.kind])
        for widget in widgets:
            if isinstance(widget,ttk.Label) and '每份 ≤' in str(widget.cget('text')):widget.configure(textvariable=self.rule)
        self.ready=True;self.bind_project();self.register_drop(controls);self.protocol('WM_DELETE_WINDOW',self.close);self.build_navigation();self.init_ai();self.post_preferences(prompt_language)
        if startup_error:self.status.set(startup_error)
    def current(self):return self.projects[self.index]
    def current_type(self):return self.current_entry() or self.current()['types'][self.kind]
    def persist(self,force=False):
        if not self.ready or self.recovery:return
        self.record_history()
        if not force and float(self.settings.get('autosave_minutes',5))==0:return
        temp=self.state_file.with_suffix('.tmp');temp.write_text(json.dumps(dict(version=3,batch=self.batch,projects=self.projects,deleted_records=getattr(self,'deleted_records',[]),history=self.history),ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,self.state_file)
    def read_state(self,path):
        path=Path(path);data=json.loads(path.read_text(encoding='utf-8'))
        self.deleted_records=data.get('deleted_records',[])
        def rebase_removed(obj):
            if isinstance(obj,dict):
                for key,value in obj.items():
                    if key=='source' and isinstance(value,str) and value and not Path(value).is_absolute():obj[key]=str(path.parent/value)
                    elif key=='photos' and isinstance(value,list):obj[key]=[str(path.parent/v) if not Path(v).is_absolute() else v for v in value]
                    elif key in ['attachments','signed'] and isinstance(value,dict):
                        for label,paths in value.items():value[label]=[str(path.parent/v) if not Path(v).is_absolute() else v for v in paths]
                    else:rebase_removed(value)
            elif isinstance(obj,list):
                for v in obj:rebase_removed(v)
        rebase_removed(self.deleted_records)
        self.history=data.get('history',[]);self.audit_previous=None
        if data.get('batch'):self.batch=data['batch']
        if data.get('version')==1 and isinstance(data.get('invoices'),list):
            p=D.project(path.stem);p['types']['零星采购']['invoices']=data['invoices'];return [p]
        if data.get('version')!=3 or not isinstance(data.get('projects'),list) or not data['projects']:raise ValueError('不支持的项目库格式')
        for p in data['projects']:
            if not isinstance(p.get('name'),str) or not p.get('id'):raise ValueError('项目缺少名称或编号')
            for kind in D.KINDS:
                t=p.get('types',{}).get(kind)
                if not isinstance(t,dict) or not isinstance(t.get('invoices'),list):raise ValueError('报销类型数据有误')
                t.setdefault('attachments',{});t.setdefault('signed',{})
                for inv in t['invoices']:
                    inv.setdefault('items',[]);inv.setdefault('photos',[]);inv.setdefault('hash','');inv.setdefault('number','')
                    src=Path(inv.get('source',''))
                    if inv.get('source') and not src.is_absolute():inv['source']=str(path.parent/src)
                    inv['photos']=[str(path.parent/v) if not Path(v).is_absolute() else v for v in inv['photos']]
                for collection in ['attachments','signed']:
                    for key,vals in t[collection].items():t[collection][key]=[str(path.parent/v) if not Path(v).is_absolute() else v for v in vals]
            for e in p.get('entries',[]):
                for inv in e['invoices']:
                    if inv.get('source') and not Path(inv['source']).is_absolute():inv['source']=str(path.parent/inv['source'])
                    inv['photos']=[str(path.parent/v) if not Path(v).is_absolute() else v for v in inv.get('photos',[])]
                for label,paths in e.get('attachments',{}).items():e['attachments'][label]=[str(path.parent/v) if not Path(v).is_absolute() else v for v in paths]
            D.sync(p)
        return data['projects']
    def bind_project(self):
        for p in self.projects:D.ensure_entries(p)
        parent_kind=D.parent_kind(self.current())
        if parent_kind:self.kind=parent_kind
        e=self.current_entry()
        if not e:
            e=next((v for v in self.current().get('entries',[]) if v['kind']==self.kind),None)
            self.entry_id=e['id'] if e else None
        if e:self.kind=e['kind']
        self.invoices=e['invoices'] if e else [];self.kind_choice.set(self.kind)
        self.entry_label.set('报销条目：'+e['name'] if e else '请在左侧新建有名称的报销条目')
        self.project_choice.configure(values=[p['name'] for p in self.projects]);self.project_choice.current(self.index);self.rule.set(D.RULES[self.kind]);self.refresh()
        self.title('CounterMiao 4.3 · '+self.batch['name'])
    def switch_project(self,event=None):
        if self.importing:self.project_choice.current(self.index);self.status.set('请等待本批导入完成再切换项目。');return
        if not self.flush_editor():return
        self.index=self.project_choice.current();self.entry_id=None;self.bind_project();self.show_overview()
    def switch_kind(self,event=None):
        if self.importing:self.kind_choice.set(self.kind);self.status.set('请等待本批导入完成再切换类型。');return
        self.kind=self.kind_choice.get();self.entry_id=None;self.bind_project()
    def create_project_record(self,name,kind):
        if kind not in D.KINDS:raise ValueError('请先选择报销类型')
        if not name.strip():raise ValueError('请填写报销项名称')
        self.flush_editor();p=D.project(name.strip(),kind);self.projects=[v for v in self.projects if not v.get('placeholder')];self.projects.append(p);self.index=len(self.projects)-1;self.kind=kind;self.entry_id=None;self.bind_project();self.show_overview();return p
    def new_project(self,on_created=None):
        if self.importing:return
        win=tk.Toplevel(self);win.title('新建报销项：先选类型，再填名称');win.geometry('540x400');win.grab_set();self.polish_dialog(win)
        win.kind_var=tk.StringVar();win.name_var=tk.StringVar()
        ttk.Label(win,text='① 请选择报销类型',font=('Microsoft YaHei UI',12,'bold')).pack(anchor='w',padx=20,pady=(18,8))
        from preferences import EN
        for kind in D.KINDS:ttk.Radiobutton(win,text=EN.get(kind,kind) if self.language=='en' else kind,variable=win.kind_var,value=kind).pack(anchor='w',padx=28,pady=3)
        ttk.Label(win,text='② 再填写报销项名称').pack(anchor='w',padx=20,pady=(12,4));win.name_entry=ttk.Entry(win,textvariable=win.name_var,state='disabled',width=48);win.name_entry.pack(padx=20,fill='x')
        def update(*args):
            chosen=win.kind_var.get() in D.KINDS;win.name_entry.configure(state='normal' if chosen else 'disabled');win.create_button.configure(state='normal' if chosen and win.name_var.get().strip() else 'disabled')
        def create():
            try:self.create_project_record(win.name_var.get(),win.kind_var.get());win.destroy()
            except Exception as e:messagebox.showerror('无法创建报销项',str(e),parent=win);return
            if on_created:self.after(0,on_created)
        bar=ttk.Frame(win);bar.pack(fill='x',padx=20,pady=18);win.create_button=ttk.Button(bar,text='创建报销项',style='Primary.TButton',command=create,state='disabled');win.create_button.pack(side='right');ttk.Button(bar,text='取消',command=win.destroy).pack(side='right',padx=8);win.kind_var.trace_add('write',update);win.name_var.trace_add('write',update);self.project_dialog=win;return win
    def rename_project(self):
        name=simpledialog.askstring('重命名','项目名称：',initialvalue=self.current()['name'],parent=self)
        if name and name.strip():self.current()['name']=name.strip();self.bind_project()
    def refresh(self):
        if not self.ready:return super().refresh()
        self.sync_all()
        selected=self.tree.selection() if hasattr(self,'tree') else ();same_entry=getattr(self,'_workspace_id',None)==self.entry_id
        super().refresh();issues=D.monthly_issues(self.projects)
        if same_entry and selected:self.tree.selection_set([row for row in selected if self.tree.exists(row)])
        batches,blocked=D.plan(self.projects,self.current(),self.kind);blocked={D.identity(i):e for i,e in blocked}
        for n,i in enumerate(self.invoices):
            values=list(self.tree.item(str(n),'values'));issue=blocked.get(D.identity(i),'')
            if issue:values[-1]=issue;self.tree.item(str(n),values=values,tags=('warn',))
            else:values[-1]='发票核对通过';self.tree.item(str(n),values=values)
        all_inv=[i for t in self.current()['types'].values() for i in t['invoices']];stats=legacy.amount_summary(all_inv)
        errors,_=D.inspect_project(self.projects,self.current())
        self.project_status.set(f'项目合计 ¥{stats["amount"]:,.2f}  /  {len(all_inv)}张  /  手动：'+('已完成' if self.current().get('manual_complete') else '整理中')+'  /  自动检查：'+('通过' if not errors else f'待处理{len(errors)}项'))
        self.update_workspace();self.persist();self.rebuild_tree()
    def poll(self):
        # Import files become owned copies so later moves of originals do not break projects.
        try:
            while True:
                kind,data=self.q.get_nowait()
                if kind=='invoice':
                    try:data['source']=D.store_file(data['source'],self.data_dir/'资料'/self.current()['id']/'发票')
                    except Exception as e:self.status.set('发票复制失败：'+str(e));continue
                    if not any(i.get('hash')==data['hash'] or (data['number'] and i['number']==data['number']) for i in self.invoices):
                        e=self.current_entry()
                        if not e:self.status.set('请先选择报销项');continue
                        data['entry_id']=e['id'];data['entry_name']=e['name'];self.invoices.append(data);self.refresh()
                elif kind=='error':messagebox.showerror('导入提示',data)
                elif kind=='progress':self.status.set(data)
                elif kind=='done':self.importing=False;self.pending_paths.clear();self.status.set(data);self.persist()
        except legacy.queue.Empty:pass
        self.after(200,self.poll)
    def save(self):
        if not self.flush_editor():return False
        if self.importing:messagebox.showinfo('请稍候','请等待发票导入完成。');return
        path=filedialog.asksaveasfilename(title='保存整个报销批次（包括材料）',initialfile=D.safe_name(self.batch['name'])+batchfile.EXT,defaultextension=batchfile.EXT,filetypes=[('报销批次文件','*'+batchfile.EXT)])
        if path:
            try:
                choice=self.encryption_choice()
                if not choice:return False
                self.persist(force=True);missing=batchfile.save_batch(path,self.batch,self.projects,getattr(self,'deleted_records',[]),password=choice[0],history=self.history);self.batch_path=path;self.batch_password=choice[0];self.file_saved_digest=self.audit_previous[0] if self.audit_previous else None;self.status.set('已保存独立批次文件：'+str(path)+('；另有缺失文件'+str(len(missing))+'个，见检查结果' if missing else ''));return True
            except Exception as e:messagebox.showerror('保存失败',str(e));return False
        return False
    def load(self):
        if self.importing:return
        path=filedialog.askopenfilename(title='打开报销批次或旧版项目数据',filetypes=[('报销批次或项目数据','*.reimbatch *.json')])
        if not path:return
        self.load_path(path)
    def load_path(self,path):
        try:
            old=self.data_dir/'批次历史';old.mkdir(exist_ok=True)
            (old/(self.batch['id']+'.json')).write_text(json.dumps(dict(version=3,batch=self.batch,projects=self.projects,deleted_records=getattr(self,'deleted_records',[])),ensure_ascii=False,indent=2),encoding='utf-8')
            is_batch=Path(path).suffix.lower()==batchfile.EXT
            password=None;original_path=path
            if is_batch:
                if batchfile.is_encrypted(path):
                    password=simpledialog.askstring('加密批次 / Encrypted batch','密码 / Password:',show='•',parent=self)
                    if password is None:return
                path=batchfile.open_batch(path,self.data_dir,password)
            incoming=self.read_state(path)
            if is_batch:
                self.projects=incoming;self.batch_path=original_path;self.batch_password=password;self.recovery=False;self.index=0;self.entry_id=None;self.bind_project();self.file_saved_digest=self.audit_previous[0] if self.audit_previous else None;self.update_file_state();return
            # Merge without silently losing current projects.
            byid={p['id']:p for p in self.projects}
            for p in incoming:
                if p['id'] in byid:
                    if not messagebox.askyesno('同名项目编号','导入项目与现有项目编号相同，是否用导入内容更新？'):continue
                    self.projects[self.projects.index(byid[p['id']])]=p
                else:self.projects.append(p)
            self.recovery=False;self.index=len(self.projects)-1;self.bind_project()
        except Exception as e:messagebox.showerror('项目库读取失败',str(e))
    def new_batch(self):
        if self.importing:return
        name=simpledialog.askstring('新建报销批次','批次名称：',parent=self)
        if not name or not name.strip():return
        old=self.data_dir/'批次历史';old.mkdir(exist_ok=True);(old/(self.batch['id']+'.json')).write_text(json.dumps(dict(version=3,batch=self.batch,projects=self.projects),ensure_ascii=False,indent=2),encoding='utf-8')
        self.batch=dict(id=D.uid(),name=name.strip());self.projects=[dict(D.project('请先新建报销项'),placeholder=True)];self.deleted_records=[];self.index=0;self.entry_id=None;self.history=[];self.audit_previous=None;self.batch_path=None;self.batch_password=None;self.bind_project()
    def complete(self):self.current()['manual_complete']=not self.current().get('manual_complete');self.refresh()
    def check(self,all_projects=False):
        targets=self.projects if all_projects else [self.current()];messages=[]
        for p in targets:
            errors,_=D.inspect_project(self.projects,p);messages.append(p['name']+'：'+('附件与规则检查通过' if not errors else '\n'+'\n'.join('• '+e for e in errors)))
        self.refresh();win=tk.Toplevel(self);win.title('自动检查结果');win.geometry('900x600');txt=tk.Text(win,wrap='word');txt.pack(fill='both',expand=True,padx=15,pady=15);txt.insert('1.0','\n\n'.join(messages)+'\n\n图片不是必需附件。检查确认文件存在、非空且可读，不验证签字真实性或审批内容。');txt.configure(state='disabled')
    def attachments(self):
        if self.importing:return
        if not self.current_entry():messagebox.showinfo('请选择报销项','请在左侧新建或选择一个报销项。');return
        kind=self.kind;t=self.current_type();batches,blocked=D.plan(self.projects,self.current(),kind)
        signed=self.current()['types'][kind]['signed']
        def bucket(collection):return signed if collection=='signed' else t['attachments']
        win=tk.Toplevel(self);win.title(kind+' · 附件与签字验收单');win.geometry('1000x620');win.grab_set()
        ttk.Label(win,text='按材料类别上传。签字扫描件逐份对应验收单；更改发票内容或分组后须重新检查对应关系。',wraplength=950).pack(padx=15,pady=12)
        table=ttk.Treeview(win,columns=('name','status'),show='headings');table.heading('name',text='所需材料 / 验收单');table.heading('status',text='关联文件');table.column('name',width=530);table.column('status',width=380);table.pack(fill='both',expand=True,padx=15)
        slots=[]
        for key in D.REQUIRED[kind]:slots.append(('attachments',key,key))
        if kind=='差旅报销':slots.append(('attachments','其他差旅材料（可选）','电子登机牌等其他差旅材料（可选）'))
        else:
            for b in batches:
                if any(i.get('entry_id')==self.entry_id for i in b['invoices']):slots.append(('signed',b['id'],f'签字验收单 {b["id"]} · {b["amount"]:.2f}元 · '+','.join(i['number'] for i in b['invoices'])))
        def redraw():
            table.delete(*table.get_children())
            for n,(collection,key,label) in enumerate(slots):
                vals=bucket(collection).get(key,[]);table.insert('','end',iid=str(n),values=(label,'；'.join(Path(v).name for v in vals) if vals else '未上传'))
        def upload():
            s=table.selection()
            if not s:return
            collection,key,_=slots[int(s[0])]
            filt=[('签字扫描件','*.pdf *.png *.jpg *.jpeg *.tif *.tiff')] if collection=='signed' else [('附件','*.*')]
            paths=filedialog.askopenfilenames(parent=win,filetypes=filt)
            if not paths:return
            try:bucket(collection)[key]=list(dict.fromkeys(bucket(collection).get(key,[])+[D.store_file(v,self.data_dir/'资料'/self.current()['id']/kind/collection) for v in paths]));redraw();self.refresh()
            except Exception as e:messagebox.showerror('附件导入失败',str(e),parent=win)
        def clear():
            s=table.selection()
            if s:collection,key,_=slots[int(s[0])];bucket(collection).pop(key,None);redraw();self.refresh()
        def open_files():
            s=table.selection()
            if s:
                collection,key,_=slots[int(s[0])];paths=bucket(collection).get(key,[])
                if paths:
                    try:os.startfile(str(Path(paths[0]).parent))
                    except Exception as e:messagebox.showerror('无法打开',str(e))
        bar=ttk.Frame(win);bar.pack(pady=12)
        for label,cmd in [('添加附件',upload),('清除关联',clear),('打开附件文件夹',open_files)]:ttk.Button(bar,text=label,command=cmd).pack(side='left',padx=6)
        ttk.Label(win,text='发票'+('核对存在问题，需先处理后才能规划签字验收单。' if blocked else '与相关材料按项目分别保存。')).pack(pady=8);redraw()
    def generate(self):
        if self.importing:return
        batches,blocked=D.plan(self.projects,self.current(),self.kind)
        if blocked:messagebox.showinfo('需先核对发票','\n'.join(D.identity(i)+'：'+e for i,e in blocked));return
        if not batches:messagebox.showinfo('没有发票','请先导入并核对当前类型的发票。');return
        root=filedialog.askdirectory(title='选择表格输出位置')
        if not root:return
        dest=Path(root)/(D.safe_name(self.current()['name'])+'_'+self.kind+'_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'));dest.mkdir()
        try:
            if self.kind=='差旅报销':D.travel_table(self.current()['types'][self.kind]['invoices'],dest/'差旅报销表.xlsx')
            else:
                for b in batches:
                    document_batch=dict(b);document_batch['invoices']=[dict(i,photos=[v for v in i.get('photos',[]) if D.readable(v)]) for i in b['invoices']]
                    legacy.build_doc(document_batch,dest/f'验收单_{b["id"]}.docx')
            self.status.set('已生成 '+str(dest));os.startfile(dest)
        except Exception as e:messagebox.showerror('生成失败',str(e))
    def archive(self):
        if self.importing:return
        results=[(p,D.inspect_project(self.projects,p)[0]) for p in self.projects];incomplete=[p['name'] for p,e in results if e]
        if incomplete and not messagebox.askyesno('仍有未通过检查的项目','以下项目材料或规则尚未通过：\n'+'\n'.join(incomplete)+'\n\n仍导出整理草稿材料包？缺件只记录在独立检查清单中。'):return
        root=filedialog.askdirectory(title='选择新的归档位置')
        if not root:return
        try:dest=D.export_all(self.projects,root);self.status.set('已归档 '+str(dest));os.startfile(dest)
        except Exception as e:messagebox.showerror('归档未完成',str(e))
    def close(self):
        if not self.flush_editor():return
        if self.importing:messagebox.showinfo('请稍候','发票仍在导入，请完成后关闭。');return
        from preferences import tr
        if self.autosave_busy:messagebox.showinfo('自动保存 / Auto-save','正在保存批次，请稍候 / A batch save is in progress.');return
        decision=messagebox.askyesnocancel(tr('保存批次工作',self.language),tr('是否保存当前报销批次后退出？\n“是”保存，“否”不另存直接退出，“取消”继续编辑。',self.language),parent=self)
        if decision is None:return
        if decision and not self.save():return
        if self.api_server:self.api_server.close();self.api_server=None
        self.persist();self.destroy()

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        import regression
        try:regression.run(sys.argv[2])
        except Exception:
            root=Path(sys.argv[2]);root.mkdir(parents=True,exist_ok=True);(root/'error.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
    else:
        window=App()
        if len(sys.argv)==2 and Path(sys.argv[1]).is_file():window.after(200,lambda:window.load_path(sys.argv[1]))
        window.mainloop()
