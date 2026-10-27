import os,json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import domain as D

from overview import ProjectOverviewMixin
from material_actions import MaterialActionsMixin

class WorkspaceMixin(MaterialActionsMixin,ProjectOverviewMixin):
    def edit(self):
        if self.selected() is None:messagebox.showinfo('请选择发票','请先在发票列表中选择一张发票，再修改内容。');return
        if not getattr(self,'_review_continuing',False):
            self._review_indices=self.selected_invoice_indices()
            if len(self._review_indices)==1:self._review_indices=list(range(self._review_indices[0],len(self.invoices)))
        self._review_continuing=False;win=super().edit()
        if win:
            def cancel():self._review_indices=[];win.destroy()
            win.protocol('WM_DELETE_WINDOW',cancel)
        self.review_window=win;return win
    def build_workspace(self,main):
        for w in main.pack_slaves():w.pack_forget()
        self.apply_polished_style();self.workspace=ttk.Frame(main,padding=(18,12));self.workspace.pack(fill='both',expand=True);self.workspace.columnconfigure(0,weight=1);self.workspace.rowconfigure(4,weight=1)
        self.page_header(self.workspace).grid(row=0,column=0,sticky='ew',pady=(0,12))
        heading=ttk.Frame(self.workspace);heading.grid(row=1,column=0,sticky='ew',pady=(0,10));self.entry_breadcrumb=tk.StringVar();self.entry_title=tk.StringVar();ttk.Label(heading,textvariable=self.entry_breadcrumb,style='Muted.TLabel').pack(anchor='w');ttk.Label(heading,textvariable=self.entry_title,style='Title.TLabel',font=('Microsoft YaHei UI',17,'bold')).pack(anchor='w',pady=(4,0))
        details=ttk.Frame(self.workspace);details.grid(row=2,column=0,sticky='ew',pady=(0,10));details.columnconfigure(1,weight=1)
        self.project_choice=ttk.Combobox(details,state='readonly',width=20);self.project_choice.bind('<<ComboboxSelected>>',self.switch_project)
        self.kind_choice=ttk.Combobox(details,state='disabled',values=D.KINDS,width=12)
        self.entry_caption=tk.StringVar();self.entry_name_var=tk.StringVar();self.entry_notes_var=tk.StringVar()
        ttk.Label(details,text='条目名称').grid(row=0,column=0,sticky='w',padx=(0,10));self.entry_name_input=ttk.Entry(details,textvariable=self.entry_name_var);self.entry_name_input.grid(row=0,column=1,sticky='ew')
        self.save_entry_button=ttk.Button(details,text='保存条目修改',command=self.save_entry_details);self.save_entry_button.grid(row=0,column=2,padx=(8,0))
        ttk.Button(details,text='返回报销项总览',command=self.show_overview).grid(row=0,column=3,padx=(8,0))
        ttk.Label(details,text='说明 / 用途').grid(row=1,column=0,sticky='w',padx=(0,10),pady=(6,0));self.entry_notes_input=ttk.Entry(details,textvariable=self.entry_notes_var);self.entry_notes_input.grid(row=1,column=1,columnspan=3,sticky='ew',pady=(6,0))
        stats=ttk.Frame(self.workspace);stats.grid(row=3,column=0,sticky='ew',pady=(0,8));ttk.Label(stats,textvariable=self.total_text,font=('Microsoft YaHei UI',11,'bold')).pack(side='left');self.entry_summary=tk.StringVar();ttk.Label(stats,textvariable=self.entry_summary,style='Muted.TLabel').pack(side='right')
        self.tabs=ttk.Notebook(self.workspace);self.tabs.grid(row=4,column=0,sticky='nsew')
        invoices=ttk.Frame(self.tabs,padding=(0,8,0,0));photos=ttk.Frame(self.tabs,padding=(0,8,0,0));attachments=ttk.Frame(self.tabs,padding=(0,8,0,0));self.tabs.add(invoices,text='发票与内容修改');self.tabs.add(photos,text='发票配图');self.tabs.add(attachments,text='其他附件 / 签字件')
        for page in (invoices,photos,attachments):page.columnconfigure(0,weight=1);page.rowconfigure(1,weight=1)
        bar=ttk.Frame(invoices);bar.grid(row=0,column=0,sticky='ew',pady=(0,8))
        self.invoice_buttons={}
        for label,command,style in [('导入发票',self.add,'Primary.TButton'),('导入文件夹',self.add_folder,'TButton'),('核对 / 修改发票内容',self.edit,'TButton'),('移除发票',self.remove,'Danger.TButton')]:
            button=ttk.Button(bar,text=label,command=command,style=style);button.pack(side='left',padx=(0,6));self.invoice_buttons[label]=button
        frame=ttk.Frame(invoices);frame.grid(row=1,column=0,sticky='nsew');frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(frame,columns=('file','number','amount','count','photos','status'),show='headings',selectmode='extended',height=4)
        for col,text,width in [('file','发票文件',180),('number','发票号码',150),('amount','金额（元）',105),('count','明细',50),('photos','配图',50),('status','核对状态',210)]:self.tree.heading(col,text=text);self.tree.column(col,width=width,minwidth=40,anchor='e' if col=='amount' else 'w')
        self.tree.grid(row=0,column=0,sticky='nsew');ys=ttk.Scrollbar(frame,command=self.tree.yview);ys.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=ys.set);self.fit_columns(self.tree,dict(file=23,number=19,amount=13,count=7,photos=7,status=31))
        self.table_tooltips(self.tree);self.tree.tag_configure('warn',background='#fff4e1');self.tree.bind('<Double-1>',lambda event:self.edit());self.tree.bind('<<TreeviewSelect>>',self.select_invoice_for_photos)
        self.invoice_empty=self.empty_state(frame,'从一张发票开始','支持拖入 PDF、图片或整个文件夹。识别后请核对金额与销售方。',self.add,'导入发票')
        self.selection_controls(invoices,self.tree).grid(row=2,column=0,sticky='ew',pady=(6,0))
        pbar=ttk.Frame(photos);pbar.grid(row=0,column=0,sticky='ew',pady=(0,8));ttk.Label(pbar,text='对应发票').pack(side='left');self.photo_invoice_choice=ttk.Combobox(pbar,state='readonly',width=23);self.photo_invoice_choice.pack(side='left',padx=6)
        self.photo_add=ttk.Button(pbar,text='添加图片',style='Primary.TButton',command=self.add_invoice_photos);self.photo_add.pack(side='left');ttk.Button(pbar,text='文件夹',command=self.add_photo_folder).pack(side='left',padx=6);self.photo_open=ttk.Button(pbar,text='打开图片',command=self.open_photo);self.photo_open.pack(side='left',padx=6);self.photo_remove=ttk.Button(pbar,text='移除图片',style='Danger.TButton',command=self.remove_photo);self.photo_remove.pack(side='left')
        photo_frame=ttk.Frame(photos);photo_frame.grid(row=1,column=0,sticky='nsew');photo_frame.columnconfigure(0,weight=1);photo_frame.rowconfigure(0,weight=1)
        self.photo_tree=ttk.Treeview(photo_frame,columns=('invoice','file'),show='tree headings',style='Photo.Treeview',selectmode='extended',height=3);self.photo_tree.heading('#0',text='预览');self.photo_tree.column('#0',width=90,stretch=False);self.photo_tree.heading('invoice',text='对应发票');self.photo_tree.heading('file',text='图片文件');self.photo_tree.grid(row=0,column=0,sticky='nsew');pys=ttk.Scrollbar(photo_frame,command=self.photo_tree.yview);pys.grid(row=0,column=1,sticky='ns');self.photo_tree.configure(yscrollcommand=pys.set);self.photo_tree.bind('<Double-1>',lambda e:self.open_photo());self.photo_tree.bind('<<TreeviewSelect>>',lambda e:self.update_material_buttons())
        self.photo_empty=self.empty_state(photo_frame,'图片为可选材料','先导入发票，再选择对应发票添加图片；支持一张或多张。')
        self.selection_controls(photos,self.photo_tree,lambda:getattr(self,'_photo_rows',{})).grid(row=2,column=0,sticky='ew',pady=(6,0))
        abar=ttk.Frame(attachments);abar.grid(row=0,column=0,sticky='ew',pady=(0,8));self.attachment_choice=ttk.Combobox(abar,state='readonly',width=28);self.attachment_choice.pack(side='left',padx=(0,6))
        self.attachment_add=ttk.Button(abar,text='添加附件',style='Primary.TButton',command=self.add_entry_attachments);self.attachment_add.pack(side='left');ttk.Button(abar,text='文件夹',command=self.add_attachment_folder).pack(side='left',padx=6);self.attachment_open=ttk.Button(abar,text='打开附件',command=self.open_entry_attachment);self.attachment_open.pack(side='left',padx=6);self.attachment_remove=ttk.Button(abar,text='移除关联',style='Danger.TButton',command=self.remove_entry_attachment);self.attachment_remove.pack(side='left')
        attach_frame=ttk.Frame(attachments);attach_frame.grid(row=1,column=0,sticky='nsew');attach_frame.rowconfigure(0,weight=1);attach_frame.columnconfigure(0,weight=1)
        self.attachment_tree=ttk.Treeview(attach_frame,columns=('kind','file'),show='headings',selectmode='extended',height=3);self.attachment_tree.heading('kind',text='材料类别');self.attachment_tree.heading('file',text='文件 / 状态');self.attachment_tree.grid(row=0,column=0,sticky='nsew');ays=ttk.Scrollbar(attach_frame,command=self.attachment_tree.yview);ays.grid(row=0,column=1,sticky='ns');self.attachment_tree.configure(yscrollcommand=ays.set);self.fit_columns(self.attachment_tree,dict(kind=38,file=62));self.attachment_tree.bind('<Double-1>',lambda e:self.open_entry_attachment());self.attachment_tree.bind('<<TreeviewSelect>>',lambda e:self.update_material_buttons());self.attachment_tree.tag_configure('missing',foreground='#aa5515')
        self.selection_controls(attachments,self.attachment_tree,lambda:getattr(self,'_attachment_rows',{})).grid(row=2,column=0,sticky='ew',pady=(6,0))
        self.entry_footer,self.entry_generate=self.page_footer(self.workspace);self.entry_footer.grid(row=5,column=0,sticky='ew',pady=(10,0))
        self._workspace_id=None;self._workspace_snapshot=None;self._photo_rows={};self._attachment_rows={};self._attachment_targets={};self._photo_images=[];self.entry_name_var.trace_add('write',lambda *a:self.update_file_state());self.entry_notes_var.trace_add('write',lambda *a:self.update_file_state());self.register_drop(invoices);self.register_drop(photos);self.register_drop(attachments);
        for table,kind in [(self.tree,'invoices'),(self.photo_tree,'photos'),(self.attachment_tree,'attachments')]:table.bind('<Button-3>',lambda event,target=table,mode=kind:self.show_material_context(event,target,mode))
        self.bind_project();self.build_overview(main)
    def update_material_buttons(self):
        if not hasattr(self,'photo_add'):return
        has_entry=self.current_entry() is not None;has_invoice=bool(self.invoices);photo_selected=bool(self.photo_tree.selection());attach_selected=bool(self.attachment_tree.selection() and self.attachment_tree.selection()[0] in self._attachment_rows)
        self.photo_add.configure(state='normal' if has_invoice and self.kind!='差旅报销' else 'disabled');self.photo_open.configure(state='normal' if photo_selected else 'disabled');self.photo_remove.configure(state='normal' if photo_selected else 'disabled');self.attachment_add.configure(state='normal' if has_entry else 'disabled');self.attachment_open.configure(state='normal' if attach_selected else 'disabled');self.attachment_remove.configure(state='normal' if attach_selected else 'disabled')
        selected=self.selected() is not None
        for key in ['核对 / 修改发票内容','移除发票']:self.invoice_buttons[key].configure(state='normal' if selected else 'disabled')
    def editor_dirty(self):
        return self._workspace_snapshot is not None and (self.entry_name_var.get(),self.entry_notes_var.get())!=self._workspace_snapshot
    def flush_editor(self):
        self.commit_overview_editor()
        if not hasattr(self,'entry_name_var') or not self.editor_dirty():return True
        e=next((e for p in self.projects for e in p.get('entries',[]) if e['id']==self._workspace_id),None)
        if not e:return True
        name=self.entry_name_var.get().strip()
        if not name:messagebox.showerror('条目名称不能为空','请输入条目名称后再继续。');return False
        e.update(name=name,notes=self.entry_notes_var.get());self._workspace_snapshot=(self.entry_name_var.get(),self.entry_notes_var.get());self.sync_all();return True
    def save_entry_details(self):
        if self.flush_editor():self.refresh();self.status.set('报销条目内容已保存。')
    def update_workspace(self):
        self.update_overview()
        if not hasattr(self,'entry_name_var'):return
        e=self.current_entry();eid=e['id'] if e else None
        if eid!=self._workspace_id or not self.editor_dirty():
            self.entry_name_var.set(e['name'] if e else '');self.entry_notes_var.set(e.get('notes','') if e else '');self._workspace_snapshot=(self.entry_name_var.get(),self.entry_notes_var.get())
        from preferences import EN
        english=self.language=='en';kind_label=EN.get(self.kind,self.kind) if english else self.kind
        self.entry_title.set(e['name'] if e else ('Select or create an entry' if english else '选择或新建报销条目'));self.entry_breadcrumb.set(self.batch['name']+'  /  '+self.current()['name']+'  /  '+kind_label);pending=sum(not i.get('confirmed') for i in self.invoices);self.entry_summary.set(f'{len(self.invoices)} invoices · {pending} to review' if english else f'{len(self.invoices)} 张发票 · 待核对 {pending} 张')
        self.invoice_empty.place_forget()
        if not self.invoices:self.invoice_empty.place(relx=.5,rely=.5,anchor='center')
        self._workspace_id=eid;state='normal' if e else 'disabled';self.entry_name_input.configure(state=state);self.entry_notes_input.configure(state=state);self.save_entry_button.configure(state=state)
        self.entry_caption.set('正在编辑：'+e['name']+' · 类型继承自报销项：'+e['kind'] if e else '请在左侧选择报销条目；没有条目时先点击“新建报销条目”。')
        choices=[f'{n+1}. '+(i.get('number') or Path(i['source']).name) for n,i in enumerate(self.invoices)];self.photo_invoice_choice.configure(values=choices)
        if choices and not 0<=self.photo_invoice_choice.current()<len(choices):self.photo_invoice_choice.current(0)
        if not choices:self.photo_invoice_choice.set('')
        photo_selection=self.photo_tree.selection() if eid==getattr(self,'_material_entry_id',None) else ();attachment_selection=self.attachment_tree.selection() if eid==getattr(self,'_material_entry_id',None) else ();self._material_entry_id=eid
        self.photo_tree.delete(*self.photo_tree.get_children());self._photo_rows={};self._photo_images=[]
        for n,i in enumerate(self.invoices):
            for j,path in enumerate(i.get('photos',[])):
                key=f'{n}:{j}';self._photo_rows[key]=(n,j,path);self.photo_tree.insert('','end',iid=key,values=(i.get('number','') or Path(i['source']).name,Path(path).name))
                try:
                    from PIL import Image,ImageTk,ImageOps
                    with Image.open(path) as original:preview=ImageOps.exif_transpose(original);preview.thumbnail((76,54));photo=ImageTk.PhotoImage(preview.copy())
                    self._photo_images.append(photo);self.photo_tree.item(key,image=photo)
                except Exception:pass
        self._slots=[];self.attachment_tree.delete(*self.attachment_tree.get_children());self._attachment_rows={};self._attachment_targets={}
        self.photo_empty.winfo_children()[0].configure(text=('Travel needs no photos' if english else '差旅报销无需配图') if self.kind=='差旅报销' else ('Photos are optional' if english else '图片为可选材料'))
        self.photo_empty.place_forget()
        if not self._photo_rows:self.photo_empty.place(relx=.5,rely=.5,anchor='center')
        if not e:self.attachment_choice.configure(values=[]);self.attachment_choice.set('');self.update_material_buttons();return
        for label in D.REQUIRED[e['kind']]+['其他附件（可选）']:self._slots.append(('attachments',label,label))
        for label in e.get('attachments',{}):
            if not any(key==label and kind=='attachments' for kind,key,_ in self._slots):self._slots.append(('attachments',label,label))
        if e['kind']!='差旅报销':
            for b in D.plan(self.projects,self.current(),e['kind'])[0]:
                if any(i.get('entry_id')==e['id'] for i in b['invoices']):self._slots.append(('signed',b['id'],'签字验收单 '+b['id']))
        for index,(kind,key,label) in enumerate(self._slots):
            bucket=e['attachments'] if kind=='attachments' else self.current()['types'][e['kind']]['signed'];paths=bucket.get(key,[])
            if not paths:
                iid=f'slot:{index}';self._attachment_targets[iid]=(kind,key);self.attachment_tree.insert('','end',iid=iid,values=(label,'未添加（可选）' if '可选' in label else '需补充'),tags=() if '可选' in label else ('missing',))
            for n,path in enumerate(paths):
                iid=f'{index}:{n}';self._attachment_targets[iid]=(kind,key);self._attachment_rows[iid]=(kind,key,n,path);self.attachment_tree.insert('','end',iid=iid,values=(label,Path(path).name))
        labels=[label for _,_,label in self._slots];self.attachment_choice.configure(values=labels)
        if labels and not 0<=self.attachment_choice.current()<len(labels):self.attachment_choice.current(0)
        self.photo_tree.selection_set([row for row in photo_selection if self.photo_tree.exists(row)]);self.attachment_tree.selection_set([row for row in attachment_selection if self.attachment_tree.exists(row)])
        for table in (self.tree,self.photo_tree,self.attachment_tree):table._update_selection_count()
        self.update_material_buttons();self.update_file_state()
    def select_invoice_for_photos(self,event=None):
        self.update_material_buttons()
        if hasattr(self,'photo_invoice_choice') and self.selected() is not None:self.photo_invoice_choice.current(self.selected())
    def attach_photo_paths(self,index,paths):
        if self.kind=='差旅报销':raise ValueError('差旅报销无需配图')
        if not 0<=index<len(self.invoices):raise ValueError('请先导入并选择一张发票')
        self.invoices[index]['photos']=self.stored_material_paths(paths,self.data_dir/'资料'/self.current()['id']/self.entry_id/'图片',self.invoices[index].get('photos',[]));self.refresh()
    def add_invoice_photos(self):
        try:
            index=self.photo_target_index()
            if index is None:raise ValueError('请先选择对应发票。')
            paths=filedialog.askopenfilenames(title='选择图片（支持多选、Ctrl+A全选）',filetypes=[('图片','*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp')])
            if paths:self.import_material_paths('photos',paths,index=index)
        except Exception as error:messagebox.showerror('图片添加失败',str(error),parent=self)
    def attach_entry_paths(self,collection,key,paths):
        e=self.current_entry()
        if not e:raise ValueError('请选择报销条目')
        bucket=e['attachments'] if collection=='attachments' else self.current()['types'][e['kind']]['signed']
        bucket[key]=self.stored_material_paths(paths,self.data_dir/'资料'/self.current()['id']/e['id']/'附件',bucket.get(key,[]));self.refresh()
    def add_entry_attachments(self):
        try:
            if self.attachment_choice.current()<0:raise ValueError('请先选择附件类别。')
            paths=filedialog.askopenfilenames(title='选择附件（支持多选、Ctrl+A全选）',filetypes=[('附件','*.*')])
            if paths:self.import_material_paths('attachments',paths)
        except Exception as error:messagebox.showerror('附件添加失败',str(error),parent=self)
