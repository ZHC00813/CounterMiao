import tkinter as tk
from tkinter import ttk
from pathlib import Path
import legacy

class DesignMixin:
    def apply_polished_style(self):
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',font=('Microsoft YaHei UI',10),background='#ffffff',foreground='#26352d')
        style.configure('TFrame',background='white');style.configure('TLabel',background='white')
        style.configure('Muted.TLabel',foreground='#65736b');style.configure('Title.TLabel',font=('Microsoft YaHei UI',17,'bold'),foreground='#26352d')
        style.configure('TButton',padding=(10,7),background='#ffffff',foreground='#26352d',borderwidth=1,relief='raised',bordercolor='#b8c5bd',lightcolor='#ffffff',darkcolor='#b8c5bd',focuscolor='#217346')
        style.map('TButton',background=[('disabled','#f2f4f3'),('pressed','#e4e9e6'),('active','#f1f4f2')],foreground=[('disabled','#89938c')],bordercolor=[('focus','#217346'),('active','#849b8d')])
        style.configure('Primary.TButton',background='#217346',foreground='white',bordercolor='#217346',lightcolor='#217346',darkcolor='#185c37',padding=(13,7))
        style.map('Primary.TButton',background=[('disabled','#e6eae7'),('pressed','#10452a'),('active','#185c37')],foreground=[('disabled','#879389'),('!disabled','white')])
        style.configure('Danger.TButton',foreground='#b43a3a');style.map('Danger.TButton',foreground=[('disabled','#89938c'),('!disabled','#b43a3a')])
        style.configure('TMenubutton',padding=(10,7),background='white',bordercolor='#b8c5bd',relief='raised')
        style.configure('TEntry',padding=5,fieldbackground='white',bordercolor='#b8c5bd');style.map('TEntry',bordercolor=[('focus','#217346')])
        style.configure('TCombobox',padding=5,bordercolor='#b8c5bd',arrowsize=12);style.map('TCombobox',fieldbackground=[('readonly','white'),('disabled','#f4f5f4')],selectbackground=[('readonly','#217346')],selectforeground=[('readonly','white')])
        style.configure('Treeview',rowheight=32,borderwidth=0,font=('Microsoft YaHei UI',10),background='white',fieldbackground='white',foreground='#26352d')
        style.configure('Treeview.Heading',background='#f2f4f3',foreground='#526259',padding=(6,8),font=('Microsoft YaHei UI',10,'bold'),relief='flat')
        style.map('Treeview',background=[('selected','#217346')],foreground=[('selected','white')]);style.configure('Photo.Treeview',rowheight=66)
        style.configure('TNotebook',borderwidth=0,tabmargins=(0,0,0,0));style.configure('TNotebook.Tab',padding=(14,8),background='#f1f3f2',bordercolor='#d6ddd8')
        style.map('TNotebook.Tab',background=[('selected','white')],foreground=[('selected','#217346')]);style.configure('TLabelframe',bordercolor='#e0e5e2',padding=8)
        style.configure('TRadiobutton',background='white',padding=4);style.configure('TCheckbutton',background='white',padding=3)
        self.option_add('*Font',('Microsoft YaHei UI',10));self.configure(background='white')
    def page_header(self,parent):
        head=ttk.Frame(parent)
        if not hasattr(self,'_page_logo'):
            try:
                from PIL import Image,ImageTk
                self._page_logo=ImageTk.PhotoImage(Image.open(legacy.BASE/'CounterMiao.png').resize((28,28)))
            except Exception:self._page_logo=None
        if self._page_logo:ttk.Label(head,image=self._page_logo).pack(side='left',padx=(0,8))
        ttk.Label(head,text='CounterMiao',font=('Microsoft YaHei UI',13,'bold'),foreground='#217346').pack(side='left')
        ttk.Button(head,text='保存批次',style='Primary.TButton',command=self.save).pack(side='right');ttk.Button(head,text='打开批次',command=self.load).pack(side='right',padx=8)
        return head
    def page_footer(self,parent):
        footer=ttk.Frame(parent);ttk.Separator(footer).pack(fill='x',pady=(0,10));bar=ttk.Frame(footer);bar.pack(fill='x')
        generate=ttk.Button(bar,text='生成本报销项表单',style='Primary.TButton',command=self.generate);generate.pack(side='left')
        ttk.Button(bar,text='检查报销项',command=self.check).pack(side='left',padx=8);ttk.Button(bar,text='导出文件清单',command=self.export_inventory).pack(side='left')
        more=ttk.Menubutton(bar,text='更多操作');more.pack(side='right');menu=tk.Menu(more,tearoff=False);more.configure(menu=menu)
        for label,cmd in [('归档整个批次',self.archive),('标记完成 / 撤销',self.complete),('检查全部报销项',lambda:self.check(True)),('查看报销规则',self.rules_dialog),('AI / 操作接口',self.ai_panel)]:menu.add_command(label=label,command=cmd)
        if not hasattr(self,'file_state'):
            self.file_state=tk.StringVar(value='批次文件：尚未另存');self.compact_status=tk.StringVar();self.status.trace_add('write',lambda *a:self.update_file_state())
        line=ttk.Frame(footer);line.pack(fill='x',pady=(8,0));ttk.Label(line,textvariable=self.file_state,style='Muted.TLabel').pack(side='left');ttk.Label(line,text='输出范围：当前报销项；归档为整个批次',style='Muted.TLabel').pack(side='right')
        ttk.Label(footer,textvariable=self.compact_status,style='Muted.TLabel',anchor='w').pack(fill='x',pady=(3,0))
        return footer,generate
    def update_file_state(self):
        if not hasattr(self,'file_state'):return
        path=getattr(self,'batch_path',None);digest=self.audit_previous[0] if getattr(self,'audit_previous',None) else None
        dirty=(digest!=getattr(self,'file_saved_digest',None) or (hasattr(self,'entry_name_var') and self.editor_dirty()) or bool(getattr(self,'overview_editor',None)))
        if self.language=='en':value=('Unsaved batch file' if not path else Path(path).name+(' · Changes not saved' if dirty else ' · Saved'))
        else:value=('批次文件：尚未另存' if not path else Path(path).name+(' · 有更改未保存' if dirty else ' · 已保存'))
        self.file_state.set(value);text=self.status.get().replace('\n',' ');self.compact_status.set(text[:90]+('…' if len(text)>90 else ''))
    def polish_dialog(self,win):
        if getattr(win,'_cm_styled',False):return
        win._cm_styled=True;win.configure(background='white')
        try:win.iconbitmap(str(legacy.BASE/'CounterMiao.ico'))
        except tk.TclError:pass
        def place():
            if not win.winfo_exists():return
            win.update_idletasks();sw=win.winfo_screenwidth();sh=win.winfo_screenheight();w=min(win.winfo_width(),sw-60);h=min(win.winfo_height(),sh-100);x=max(0,min(self.winfo_rootx()+(self.winfo_width()-w)//2,sw-w));y=max(0,min(self.winfo_rooty()+(self.winfo_height()-h)//2,sh-h-40));win.geometry(f'{w}x{h}+{x}+{y}')
        win.after_idle(place)
    def fit_columns(self,table,weights):
        def resize(event):
            if getattr(self,'overview_editor',None):return
            available=max(100,event.width-4);total=sum(weights.values())
            for col,weight in weights.items():table.column(col,width=max(48,int(available*weight/total)),minwidth=40,stretch=False)
        table.bind('<Configure>',resize,add='+')
    def empty_state(self,parent,title,description,action=None,label=None):
        panel=ttk.Frame(parent,padding=16);ttk.Label(panel,text=title,font=('Microsoft YaHei UI',12,'bold')).pack(pady=(0,8));ttk.Label(panel,text=description,style='Muted.TLabel',wraplength=450,justify='center').pack()
        if action:ttk.Button(panel,text=label,style='Primary.TButton',command=action).pack(pady=(12,0))
        return panel

    def rules_dialog(self):
        win=tk.Toplevel(self);win.title('报销规则');win.geometry('560x240');self.polish_dialog(win);body=ttk.Frame(win,padding=24);body.pack(fill='both',expand=True);ttk.Label(body,text=self.kind,style='Title.TLabel',font=('Microsoft YaHei UI',17,'bold')).pack(anchor='w');ttk.Label(body,text=self.rule.get(),wraplength=480).pack(anchor='w',pady=16);ttk.Button(body,text='关闭',command=win.destroy).pack(anchor='e')

    def table_tooltips(self,table):
        state={'cell':None,'timer':None,'tip':None}
        def hide(event=None):
            if state['timer']:
                try:table.after_cancel(state['timer'])
                except tk.TclError:pass
            state['timer']=None;state['cell']=None
            if state['tip']:
                try:state['tip'].destroy()
                except tk.TclError:pass
            state['tip']=None
        def motion(event):
            row=table.identify_row(event.y);column=table.identify_column(event.x);cell=(row,column)
            if cell==state['cell']:return
            hide();state['cell']=cell
            if not row or column in ('','#0'):return
            def show():
                if not table.winfo_exists() or not table.exists(row):return
                values=table.item(row,'values');index=int(column[1:])-1
                if index>=len(values) or not str(values[index]):return
                tip=tk.Toplevel(table);tip._cm_styled=True;tip.overrideredirect(True);state['tip']=tip
                ttk.Label(tip,text=str(values[index]),wraplength=440,padding=10,relief='solid',borderwidth=1).pack();tip.geometry(f'+{min(table.winfo_pointerx()+12,table.winfo_screenwidth()-460)}+{min(table.winfo_pointery()+18,table.winfo_screenheight()-150)}')
            state['timer']=table.after(650,show)
        table.bind('<Motion>',motion,add='+');table.bind('<Leave>',hide,add='+');table.bind('<ButtonPress-1>',hide,add='+')

    def node_icon(self,kind):
        if not hasattr(self,'_node_icons'):self._node_icons={}
        if kind in self._node_icons:return self._node_icons[kind]
        im=tk.PhotoImage(width=16,height=16);green='#217346';gray='#718278'
        def rect(x1,y1,x2,y2,color):im.put(color,to=(x1,y1,x2,y2))
        if kind=='batch':
            for x in (2,9):
                for y in (2,9):rect(x,y,x+5,y+5,green)
        elif kind in ('project','folder'):
            rect(1,4,15,14,green if kind=='project' else gray);rect(2,2,7,5,green if kind=='project' else gray);rect(3,7,13,8,'#ffffff')
        elif kind=='entry':
            for y in (3,7,11):rect(2,y,4,y+2,green);rect(6,y,14,y+2,gray)
        else:
            rect(3,1,13,15,gray);rect(4,2,12,14,'#ffffff')
            for y in (5,8,11):rect(6,y,11,y+1,gray)
        self._node_icons[kind]=im;return im

    def create_upload_style(self):
        if hasattr(self,'_round_upload_images'):return
        from PIL import Image,ImageDraw,ImageTk
        style=ttk.Style(self);self._round_upload_images=[]
        for background in ('#ffffff','#f1f3f2','#e8ece9'):
            im=Image.new('RGBA',(112,112),(255,255,255,0));draw=ImageDraw.Draw(im);draw.rounded_rectangle((2,2,109,109),radius=26,fill=background,outline='#217346',width=4);self._round_upload_images.append(ImageTk.PhotoImage(im.resize((28,28),Image.Resampling.LANCZOS)))
        style.element_create('UploadRound.border','image',self._round_upload_images[0],('disabled',self._round_upload_images[2]),('active',self._round_upload_images[1]),border=4,sticky='nsew')
        style.layout('Upload.TButton',[('UploadRound.border',{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
        style.configure('Upload.TButton',font=('Microsoft YaHei UI',9),foreground='#185c37',padding=(3,0),anchor='center');style.map('Upload.TButton',foreground=[('disabled','#89938c')])
