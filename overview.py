import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from decimal import Decimal
import domain as D

def overview_amount(value):
    try:
        number=Decimal(str(value));return number if number.is_finite() else Decimal(0)
    except Exception:return Decimal(0)

def display_amount(value):
    try:
        amount=Decimal(str(value))
        if not amount.is_finite():raise ValueError()
        return f'{amount:,.2f}'
    except Exception:return '待核对'

from ui_design import DesignMixin

class ProjectOverviewMixin(DesignMixin):
    def build_overview(self,main):
        self.create_upload_style();self._upload_buttons={};self._upload_render_pending=False
        self.view_mode='entry';self.overview=ttk.Frame(main,padding=(18,12));self.overview.columnconfigure(0,weight=1);self.overview.rowconfigure(3,weight=1);self.overview_editor=None;self.overview_rows={}
        self.page_header(self.overview).grid(row=0,column=0,sticky='ew',pady=(0,12))
        heading=ttk.Frame(self.overview);heading.grid(row=1,column=0,sticky='ew',pady=(0,12));self.overview_breadcrumb=tk.StringVar();ttk.Label(heading,textvariable=self.overview_breadcrumb,style='Muted.TLabel').pack(anchor='w')
        self.overview_title=tk.StringVar();ttk.Label(heading,textvariable=self.overview_title,style='Title.TLabel',font=('Microsoft YaHei UI',17,'bold')).pack(anchor='w',pady=(4,5));self.overview_summary=tk.StringVar();ttk.Label(heading,textvariable=self.overview_summary,style='Muted.TLabel').pack(anchor='w')
        bar=ttk.Frame(self.overview);bar.grid(row=2,column=0,sticky='ew',pady=(0,10))
        ttk.Button(bar,text='新建报销条目',style='Primary.TButton',command=self.overview_new_entry).pack(side='left');ttk.Button(bar,text='编辑选中条目',command=self.overview_open_entry).pack(side='left',padx=8);ttk.Button(bar,text='修改报销项名称',command=self.rename_project).pack(side='left')
        frame=ttk.Frame(self.overview);frame.grid(row=3,column=0,sticky='nsew');frame.columnconfigure(0,weight=1);frame.rowconfigure(0,weight=1)
        cols=('name','company','invoice','amount','photos','attachment','notes');self.overview_table=ttk.Treeview(frame,columns=cols,show='headings',selectmode='browse',height=4)
        for col,label in zip(cols,['报销条目','企业名称','发票 / 添加','金额（元）','配图','附件','用途']):self.overview_table.heading(col,text=label);self.overview_table.column(col,width=100,minwidth=40,anchor='e' if col=='amount' else 'w')
        self.overview_table.grid(row=0,column=0,sticky='nsew');ys=ttk.Scrollbar(frame,command=self.overview_table.yview);ys.grid(row=0,column=1,sticky='ns');self.overview_table.configure(yscrollcommand=lambda first,last:(ys.set(first,last),self.schedule_upload_buttons()));self.overview_table.bind('<Configure>',lambda event:self.schedule_upload_buttons(),add='+');self.fit_columns(self.overview_table,dict(name=18,company=20,invoice=20,amount=12,photos=7,attachment=10,notes=13))
        self.table_tooltips(self.overview_table);self.overview_table.tag_configure('odd',background='#f7f8f7');self.overview_table.tag_configure('warn',foreground='#aa5515');self.overview_table.bind('<Double-1>',self.overview_double);self.overview_table.bind('<ButtonRelease-1>',self.overview_click);self.overview_table.bind('<Button-3>',self.show_overview_context)
        self.register_material_drop(self.overview_table,'overview')
        self.overview_empty=self.empty_state(frame,'建立第一个报销条目','每个条目归集对应发票、图片和附件；同一报销项下可统一整理。',self.overview_new_entry,'新建报销条目')
        ttk.Label(self.overview,text='双击名称、企业或用途可编辑；点击发票、配图或附件可添加材料；双击金额可核对。',style='Muted.TLabel').grid(row=4,column=0,sticky='w',pady=(8,0))
        self.overview_footer,self.overview_generate=self.page_footer(self.overview);self.overview_footer.grid(row=5,column=0,sticky='ew',pady=(10,0))
    def show_overview(self):
        if not hasattr(self,'overview'):return
        self.commit_overview_editor();self.view_mode='project';self.workspace.pack_forget();self.overview.pack(fill='both',expand=True);self.update_overview()
    def show_entry_workspace(self):
        if not hasattr(self,'overview'):return
        self.commit_overview_editor();self.view_mode='entry';self.overview.pack_forget();self.workspace.pack(fill='both',expand=True)
    def update_overview(self):
        if not hasattr(self,'overview_table'):return
        if self.overview_editor:return
        from preferences import EN
        english=self.language=='en';p=self.current();self.overview_breadcrumb.set(self.batch['name']+('  /  Group overview' if english else '  /  报销项总览'));self.overview_title.set(p['name']);entries=p.get('entries',[]);total=sum((overview_amount(i.get('amount')) for e in entries for i in e['invoices']),Decimal('0'));self.overview_summary.set(f"{D.parent_kind(p) or '旧版混合类型'}    ·    {len(entries)} 个报销条目    ·    {sum(len(e['invoices']) for e in entries)} 张发票    ·    合计 ¥{total:,.2f}    ·    {'已完成' if p.get('manual_complete') else '整理中'}")
        if english:self.overview_summary.set(f"{EN.get(D.parent_kind(p),D.parent_kind(p)) or 'Legacy mixed types'} · {len(entries)} entries · {sum(len(e['invoices']) for e in entries)} invoices · Total ¥{total:,.2f}")
        pending_amount=sum(display_amount(i.get('amount'))=='待核对' for e in entries for i in e['invoices'])
        if pending_amount:self.overview_summary.set(self.overview_summary.get()+(f' · {pending_amount} amounts to review' if english else f' · 另有{pending_amount}张金额待核对'))
        for button in self._upload_buttons.values():button.place_forget()
        selected=self.overview_table.selection();self.overview_table.delete(*self.overview_table.get_children());self.overview_rows={}
        for e in entries:
            for n,inv in enumerate(e['invoices'] or [None]):
                key=e['id']+':'+str(n);self.overview_rows[key]=(e,n if inv else None)
                values=(e['name'],inv.get('seller','') if inv else e.get('supplier_name',''),(Path(inv['source']).name if inv else ''),display_amount(inv.get('amount')) if inv else '—',str(len(inv.get('photos',[]))) if inv else '—',str(sum(len(v) for v in e.get('attachments',{}).values())),e.get('notes',''))
                tags=['odd'] if len(self.overview_rows)%2 else []
                if inv and overview_amount(inv.get('amount'))>1000:tags.append('warn')
                self.overview_table.insert('','end',iid=key,values=values,tags=tags)
        if selected and self.overview_table.exists(selected[0]):self.overview_table.selection_set(selected[0])
        self.overview_empty.place_forget()
        if not self.overview_rows:self.overview_empty.place(relx=.5,rely=.5,anchor='center')
        self.update_file_state();self.schedule_upload_buttons()
    def overview_new_entry(self):self.new_entry(on_created=self.show_overview)
    def overview_target(self,event=None):
        iid=self.overview_table.identify_row(event.y) if event else next(iter(self.overview_table.selection()),None)
        if iid not in self.overview_rows:return None
        self.overview_table.selection_set(iid);return self.overview_rows[iid]
    def overview_activate(self,e):
        if not self.flush_editor():return False
        self.entry_id=e['id'];self.kind=e['kind'];self.bind_project();return True
    def overview_open_entry(self):
        target=self.overview_target()
        if target and self.overview_activate(target[0]):self.show_entry_workspace();self.focus_entry_editor()
    def set_overview_value(self,e,index,column,value):
        if column=='name':
            if not value.strip():raise ValueError('条目名称不能为空')
            e['name']=value.strip()
        elif column=='notes':e['notes']=value
        elif column=='company':
            if index is None:e['supplier_name']=value.strip()
            else:
                inv=e['invoices'][index]
                if inv.get('seller','')!=value.strip():inv['seller']=value.strip();inv['confirmed']=False
        self._workspace_snapshot=None;self.refresh()
    def commit_overview_editor(self):
        editor=getattr(self,'overview_editor',None)
        if not editor:return
        self.overview_editor=None
        if editor.winfo_exists():
            e,index,column=editor.target;value=editor.get();editor.destroy()
            try:self.set_overview_value(e,index,column,value)
            except ValueError as ex:messagebox.showerror('无法保存',str(ex))
    def overview_double(self,event):
        target=self.overview_target(event)
        if not target:return
        column=self.overview_table.identify_column(event.x);name=self.overview_table['columns'][int(column[1:])-1] if column else ''
        if name in ('name','company','notes'):
            self.commit_overview_editor();iid=self.overview_table.identify_row(event.y);box=self.overview_table.bbox(iid,column)
            if not box:return
            editor=ttk.Entry(self.overview_table);editor.insert(0,self.overview_table.set(iid,name));editor.target=(*target,name);editor.place(x=box[0],y=box[1],width=box[2],height=box[3]);self.overview_editor=editor;self.update_file_state();editor.focus_set();editor.selection_range(0,'end');editor.bind('<Return>',lambda e:self.commit_overview_editor());editor.bind('<FocusOut>',lambda e:self.commit_overview_editor());editor.bind('<Escape>',lambda e:(setattr(self,'overview_editor',None),editor.destroy()))
        elif name=='amount' and target[1] is not None:
            if self.overview_activate(target[0]):self.tree.selection_set(str(target[1]));self.edit()
    def overview_click(self,event):
        # Upload actions live on real rounded buttons; ordinary cell clicks only select.
        return
    def overview_upload(self,iid,column):
        target=self.overview_rows.get(iid)
        if not target:return
        self.overview_table.selection_set(iid);self.commit_overview_editor();e,index=target
        if not self.overview_activate(e):return
        if column=='invoice':self.add()
        elif column=='photos' and index is not None:
            self.tree.selection_set(str(index));self.tabs.select(0);self.add_invoice_photos()
        elif column=='attachment':self.overview_attachment_picker(e)
    def schedule_upload_buttons(self):
        if getattr(self,'_upload_render_pending',False):return
        self._upload_render_pending=True;self.after_idle(self.render_upload_buttons)
    def render_upload_buttons(self):
        self._upload_render_pending=False
        if not hasattr(self,'overview_table') or not self.overview_table.winfo_exists():return
        visible=set()
        for iid,(entry,index) in self.overview_rows.items():
            for column in ('invoice','photos','attachment'):
                box=self.overview_table.bbox(iid,column)
                if not box:continue
                key=(iid,column);visible.add(key)
                if key not in self._upload_buttons:
                    button=ttk.Button(self.overview_table,style='Upload.TButton',takefocus=True);self._upload_buttons[key]=button;self.register_material_drop(button,'overview',iid,column);button.bind('<Button-3>',lambda event,row=iid:self.show_overview_context(event,row))
                button=self._upload_buttons[key];english=self.language=='en'
                inv=entry['invoices'][index] if index is not None else None
                if column=='invoice':label='Upload' if english else '上传'
                elif column=='photos':label=str(len(inv.get('photos',[])))+' +' if inv and inv.get('photos') else ('Photo' if english else '配图')
                else:label='Files' if english else '附件'
                disabled=column=='photos' and (index is None or entry['kind']=='差旅报销')
                button.configure(text=label,state='disabled' if disabled else 'normal',command=lambda row=iid,col=column:self.overview_upload(row,col))
                width=min(box[2]-6,64 if english else 54);x=box[0]+box[2]-width-3
                button.place(x=x,y=box[1]+2,width=max(20,width),height=max(22,box[3]-4));button.lift()
        for key in list(self._upload_buttons):
            if key not in visible:self._upload_buttons.pop(key).destroy()
    def overview_drop(self,event,iid=None,column=None,paths=()):
        if iid is None:
            if hasattr(event,'y_root'):x=event.x_root-self.overview_table.winfo_rootx();y=event.y_root-self.overview_table.winfo_rooty()
            else:x=getattr(event,'x',-1);y=getattr(event,'y',-1)
            iid=self.overview_table.identify_row(y);column={'#3':'invoice','#5':'photos','#6':'attachment'}.get(self.overview_table.identify_column(x))
        target=self.overview_rows.get(iid)
        if not target or not column:raise ValueError('请拖到对应行的发票、配图或附件上传按钮。')
        e,index=target
        if not self.overview_activate(e):return
        if column=='invoice':self.import_paths(paths)
        elif column=='photos':
            if index is None:raise ValueError('请先为本条目导入发票，再配图。')
            self.import_material_paths('photos',paths,index=index)
        elif column=='attachment':self.overview_attachment_picker(e,paths)
        from legacy import COPY
        return COPY
    def overview_attachment_picker(self,e,paths=None):
        win=tk.Toplevel(self);win.title('上传条目附件');win.geometry('500x210');win.grab_set();self.polish_dialog(win);ttk.Label(win,text=e['name']+' · 选择附件类别').pack(pady=(16,8));choice=ttk.Combobox(win,state='readonly',values=[label for _,_,label in self._slots],width=45);choice.pack();choice.current(0) if self._slots else None
        def upload():
            n=choice.current()
            if n<0:return
            collection,key,_=self._slots[n];chosen=paths or filedialog.askopenfilenames(parent=win,title='选择附件（支持多选）')
            if chosen:
                try:self.import_material_paths('attachments',chosen,slot=(collection,key));win.destroy()
                except Exception as error:messagebox.showerror('附件添加失败',str(error),parent=win)
        ttk.Button(win,text='导入拖入的附件' if paths else '选择文件并上传',style='Primary.TButton',command=upload).pack(pady=14)
