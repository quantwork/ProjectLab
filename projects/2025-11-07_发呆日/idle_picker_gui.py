#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZeroPhase · GUI 版灵感抽取器
功能:
- 从 idle_pool.md/.csv 随机抽取，滚动动画增强趣味
- 自动过滤关键词(默认: 交易/策略/量化)与近 N 天去重
- 支持多次抽取、打开链接、写日志 logs/idle_pick_log.csv
版本:
v0.3 · 2025-10-31
"""

import csv, os, re, random, webbrowser
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ------- 默认参数 -------
DEFAULT_POOL = r"D:\Quant\ProjectLab\projects\2025-11-07_发呆日\idle_pool.md"
DEFAULT_LOG  = r"D:\Quant\ProjectLab\projects\2025-11-07_发呆日\logs\idle_pick_log.csv"
DEFAULT_EXCL = ""  # 空格分隔 交易 策略 量化
DEFAULT_DEDUP= 30
DEFAULT_SAMPLES = 1

# ------- 工具 -------
def normalize(s:str)->str:
    return re.sub(r"\s+"," ", s.strip())

def ensure_dir(p:str):
    d=os.path.dirname(os.path.abspath(p))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def read_csv_any_encoding(path:str):
    encs=["utf-8-sig","utf-8","gbk","cp936","utf-16","utf-16-le","utf-16-be"]
    last=None
    for enc in encs:
        try:
            with open(path,"r",encoding=enc,newline="") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            last=e
            continue
    raise last

def read_pool(path:str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到清单: {path}")
    ext=os.path.splitext(path)[1].lower()
    items=[]
    if ext==".csv":
        rows=read_csv_any_encoding(path)
        for r in rows:
            t=normalize(r.get("title","") or r.get("Title",""))
            if t: items.append(t)
    else:
        with open(path,"r",encoding="utf-8-sig") as f:
            for line in f:
                line=normalize(line)
                if not line or line.startswith("#") or line.startswith(">"):
                    continue
                line=re.sub(r"^[-*\d\.)]+\s*","",line)  # 去列表前缀
                items.append(line)
    return items

def read_recent_titles(log_path:str, dedup_days:int)->set:
    if not os.path.exists(log_path): return set()
    try:
        rows=read_csv_any_encoding(log_path)
    except Exception:
        # 备份坏日志
        try:
            bak=log_path+f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.replace(log_path,bak)
        except: pass
        return set()
    cutoff=datetime.now().date()-timedelta(days=dedup_days)
    seen=set()
    for r in rows:
        d=(r or {}).get("date",""); t=(r or {}).get("title","")
        try:
            if t and datetime.strptime(d,"%Y-%m-%d").date()>=cutoff:
                seen.add(t)
        except: continue
    return seen

def append_log(log_path:str, picks:list):
    ensure_dir(log_path)
    exists=os.path.exists(log_path)
    with open(log_path,"a",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["date","time","title"])
        if not exists: w.writeheader()
        now=datetime.now()
        for t in picks:
            w.writerow({"date":now.strftime("%Y-%m-%d"),
                        "time":now.strftime("%H:%M:%S"),
                        "title":t})

def filter_candidates(items:list, excl_words:list, seen:set):
    res=[t for t in items
         if not any(w for w in excl_words if w and w in t)
         and t not in seen]
    return res

def split_title_url(s:str):
    # 允许 “标题 | 链接”
    if "|" in s:
        left,right=s.split("|",1)
        return normalize(left), normalize(right)
    return s, None

# ------- GUI -------
class ZeroPhaseGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("灵感抽取器")
        self.geometry("700x520")
        self.minsize(680,500)
        self.configure(padx=12,pady=12)
        self._build_widgets()
        self.items=[]
        self.animating=False
        self.anim_job=None

    def _build_widgets(self):
        # 行1: 路径与浏览
        frm1=ttk.Frame(self); frm1.pack(fill="x", pady=(0,8))
        ttk.Label(frm1,text="清单文件:").pack(side="left")
        self.var_pool=tk.StringVar(value=DEFAULT_POOL)
        ent_pool=ttk.Entry(frm1,textvariable=self.var_pool); ent_pool.pack(side="left",fill="x",expand=True,padx=6)
        ttk.Button(frm1,text="浏览",command=self.browse_pool).pack(side="left")

        # 行2: 关键词 / 去重天数 / 数量
        frm2=ttk.Frame(self); frm2.pack(fill="x", pady=(0,8))
        ttk.Label(frm2,text="排除词:").pack(side="left")
        self.var_excl=tk.StringVar(value=DEFAULT_EXCL)
        ttk.Entry(frm2,textvariable=self.var_excl,width=28).pack(side="left",padx=6)
        ttk.Label(frm2,text="去重天数:").pack(side="left",padx=(8,0))
        self.var_dedup=tk.IntVar(value=DEFAULT_DEDUP)
        sp1=ttk.Spinbox(frm2,from_=0,to=365,textvariable=self.var_dedup,width=6); sp1.pack(side="left",padx=4)
        ttk.Label(frm2,text="抽取数:").pack(side="left",padx=(8,0))
        self.var_samples=tk.IntVar(value=DEFAULT_SAMPLES)
        sp2=ttk.Spinbox(frm2,from_=1,to=10,textvariable=self.var_samples,width=4); sp2.pack(side="left",padx=4)
        ttk.Button(frm2,text="打开日志",command=self.open_log_dir).pack(side="right")

        # 行3: 大显示屏
        self.lbl_display=tk.Label(self,text="点击『开始抽取』",anchor="center",
                                  font=("Microsoft YaHei",16),relief="groove",height=3)
        self.lbl_display.pack(fill="x", pady=6)

        # 行4: 按钮区
        frm3=ttk.Frame(self); frm3.pack(fill="x", pady=(0,6))
        self.btn_start=ttk.Button(frm3,text="开始抽取",command=self.start_draw)
        self.btn_start.pack(side="left")
        self.btn_stop =ttk.Button(frm3,text="停止",command=self.stop_draw,state="disabled")
        self.btn_stop.pack(side="left",padx=6)
        ttk.Button(frm3,text="打开链接",command=self.open_selected_url).pack(side="left",padx=6)
        ttk.Button(frm3,text="刷新清单",command=self.reload_pool).pack(side="left",padx=6)

        # 行5: 结果列表
        self.lst=ttk.Treeview(self,columns=("title","url"),show="headings",height=10)
        self.lst.heading("title",text="结果")
        self.lst.heading("url",text="链接")
        self.lst.column("title",width=460,anchor="w")
        self.lst.column("url",width=180,anchor="w")
        self.lst.pack(fill="both",expand=True)

        # 状态栏
        self.var_status=tk.StringVar(value="就绪")
        ttk.Label(self,textvariable=self.var_status,anchor="w").pack(fill="x",pady=(6,0))

        # 主题样式微调
        try:
            self.call("tk","scaling",1.25)
        except: pass

        # 快捷键
        self.bind("<Return>", lambda e: self.start_draw() if not self.animating else self.stop_draw())
        self.bind("<Control-o>", lambda e: self.open_selected_url())

    # --- 交互 ---
    def browse_pool(self):
        p=filedialog.askopenfilename(title="选择清单文件",
                                     filetypes=[("Markdown/CSV","*.md *.csv"),("All","*.*")])
        if p:
            self.var_pool.set(p)

    def reload_pool(self):
        try:
            self.items=read_pool(self.var_pool.get())
            self.var_status.set(f"载入条目 {len(self.items)} 条")
        except Exception as e:
            messagebox.showerror("读取失败", str(e))

    def open_log_dir(self):
        ensure_dir(DEFAULT_LOG)
        os.startfile(os.path.dirname(DEFAULT_LOG))

    def start_draw(self):
        try:
            if not self.items:
                self.items=read_pool(self.var_pool.get())
        except Exception as e:
            messagebox.showerror("读取失败", str(e)); return

        excl=[w.strip() for w in self.var_excl.get().split() if w.strip()]
        seen=read_recent_titles(DEFAULT_LOG, max(0,int(self.var_dedup.get())))
        cand=filter_candidates(self.items, excl, seen)
        if not cand:
            # 退化为仅关键词过滤
            cand=[t for t in self.items if not any(w in t for w in excl)]
        if not cand:
            messagebox.showinfo("提示","无可用候选，请增加清单或放宽条件。")
            return

        self._anim_pool=cand
        self._anim_ticks=0
        self.animating=True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_display.config(text="抽取中...")
        self._animate()

    def _animate(self):
        if not self.animating: return
        self._anim_ticks+=1
        # 每次闪现随机一条，模拟转盘
        t=random.choice(self._anim_pool)
        self.lbl_display.config(text=t)
        # 1.2 秒后自动停止
        if self._anim_ticks>=18:
            self.stop_draw()
            return
        self.anim_job=self.after(60, self._animate)

    def stop_draw(self):
        if not self.animating: return
        if self.anim_job: self.after_cancel(self.anim_job)
        self.animating=False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

        samples=max(1,int(self.var_samples.get()))
        picks=random.sample(self._anim_pool, min(samples, len(self._anim_pool)))
        # 显示与日志
        for i in self.lst.get_children(): self.lst.delete(i)
        for t in picks:
            title,url=split_title_url(t)
            self.lst.insert("", "end", values=(title, url or ""))
        append_log(DEFAULT_LOG, [normalize(p) for p in picks])

        self.lbl_display.config(text="完成")
        self.var_status.set(f"抽取 {len(picks)} 条，已写入日志")

    def open_selected_url(self):
        sel=self.lst.selection()
        if not sel:
            messagebox.showinfo("提示","请选择一条结果。"); return
        _,url=self.lst.item(sel[0],"values")
        url=url.strip()
        if url:
            try:
                webbrowser.open(url)
            except Exception as e:
                messagebox.showerror("打开失败", str(e))
        else:
            messagebox.showinfo("提示","该条目未提供链接。")

if __name__=="__main__":
    app=ZeroPhaseGUI()
    app.mainloop()
