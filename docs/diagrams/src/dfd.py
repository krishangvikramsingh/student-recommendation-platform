import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
plt.rcParams["font.family"]=["Liberation Sans","DejaVu Sans"]
NAVY="#12355b"; BLUE="#1f4e79"; FILL="#e8f1fa"; GREY="#666666"
ENT="#fdf1d6"; ENTE="#b8860b"; STO="#e9f4e4"; STOE="#4b7a3a"
FOOT="Krishang Vikram Singh | Roll No. B106 | Batch C1 | B.Tech Computer Engineering"

class Canvas:
    def __init__(self,W,H,title,sub,note):
        self.W,self.H=W,H
        self.fig=plt.figure(figsize=(W,H),dpi=200)
        self.ax=self.fig.add_axes([0,0,1,1]); self.ax.set_xlim(0,W); self.ax.set_ylim(H,0); self.ax.axis("off")
        a=self.ax
        a.text(W/2,0.4,title,ha="center",va="center",fontsize=22,fontweight="bold",color=NAVY)
        a.text(W/2,0.82,sub,ha="center",va="center",fontsize=13,fontweight="bold",color=BLUE)
        a.text(W/2,1.15,note,ha="center",va="center",fontsize=9.5,style="italic",color=GREY)
        a.add_patch(Rectangle((0.15,1.4),W-0.3,H-1.4-0.15,fill=False,ec="#999",lw=1.2))
        a.text(0.3,H-0.3,FOOT,fontsize=8.5,color=GREY,va="center")
    def entity(self,x,y,w,h,text):
        a=self.ax
        a.add_patch(Rectangle((x-w/2+0.08,y-h/2-0.08),w,h,fc=ENT,ec=ENTE,lw=1.4,zorder=2))
        a.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc=ENT,ec=ENTE,lw=1.6,zorder=3))
        a.text(x,y,text,ha="center",va="center",fontsize=12,fontweight="bold",color="#5a4300",zorder=4)
    def process(self,x,y,w,h,num,text):
        a=self.ax
        a.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=0,rounding_size=0.14",fc=FILL,ec=BLUE,lw=1.6,zorder=3))
        a.plot([x-w/2,x+w/2],[y-h/2+0.34,y-h/2+0.34],color=BLUE,lw=1.1,zorder=4)
        a.text(x,y-h/2+0.17,num,ha="center",va="center",fontsize=10.5,fontweight="bold",color=NAVY,zorder=5)
        a.text(x,y+0.17,text,ha="center",va="center",fontsize=11.5,fontweight="bold",color=NAVY,zorder=5,linespacing=1.15)
    def store(self,x,y,w,h,sid,text):
        a=self.ax
        l,r,t,b=x-w/2,x+w/2,y-h/2,y+h/2
        a.add_patch(Rectangle((l,t),w,h,fc=STO,ec="none",zorder=2))
        a.plot([l+w,l,l,l+w],[t,t,b,b],color=STOE,lw=1.6,zorder=3)
        a.plot([l+0.55,l+0.55],[t,b],color=STOE,lw=1.2,zorder=3)
        a.text(l+0.275,y,sid,ha="center",va="center",fontsize=10.5,fontweight="bold",color="#2d4f21",zorder=4)
        a.text(l+0.65+(w-0.65)/2,y,text,ha="center",va="center",fontsize=11,fontweight="bold",color="#2d4f21",zorder=4)
    def flow(self,pts,label=None,lpos=None,ha="center",va="bottom"):
        a=self.ax
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        if len(pts)>2: a.plot(xs[:-1],ys[:-1],color=NAVY,lw=1.5,zorder=4,solid_capstyle="butt")
        a.annotate("",xy=pts[-1],xytext=pts[-2],arrowprops=dict(arrowstyle="-|>",color=NAVY,lw=1.5,mutation_scale=13,shrinkA=0,shrinkB=0),zorder=4)
        if len(pts)==2: pass
        if label:
            x,y=lpos
            a.text(x,y,label,ha=ha,va=va,fontsize=9.6,color="#111",zorder=6,linespacing=1.15,
                   bbox=dict(fc="white",ec="none",pad=0.9,alpha=0.92))
    def save(self,fn):
        self.fig.savefig(fn,dpi=200,facecolor="white"); plt.close(self.fig)


def legend0(c):
    a=c.ax; ly=c.H-1.35; W=c.W
    a.add_patch(Rectangle((W-5.3,ly),5.0,1.1,fc="white",ec="#999",lw=1))
    a.text(W-5.15,ly+0.2,"Legend",fontsize=10,fontweight="bold",color=NAVY,va="center")
    a.add_patch(Rectangle((W-5.15,ly+0.4),0.4,0.2,fc=ENT,ec=ENTE,lw=1.2)); a.text(W-4.6,ly+0.5,"External entity",fontsize=9,va="center",color=NAVY)
    a.add_patch(Circle((W-2.85,ly+0.5),0.14,fc=FILL,ec=BLUE,lw=1.2)); a.text(W-2.6,ly+0.5,"Process (system)",fontsize=9,va="center",color=NAVY)
    a.annotate("",xy=(W-4.7,ly+0.85),xytext=(W-5.15,ly+0.85),arrowprops=dict(arrowstyle="-|>",color=NAVY,lw=1.4,mutation_scale=11,shrinkA=0,shrinkB=0))
    a.text(W-4.6,ly+0.85,"Data flow",fontsize=9,va="center",color=NAVY)

def build_level0(fn):
    import math
    c=Canvas(13,7.7,"Data Flow Diagram — Level 0 (Context Diagram)","Student Recommendation Platform for New City Students",
             "Practical 8 — Data Flow Diagram (derived from the actors and use cases of Experiment 3)")
    a=c.ax; cx,cy,r=6.5,4.4,1.5
    a.add_patch(Circle((cx,cy),r,fc=FILL,ec=BLUE,lw=2,zorder=3))
    a.plot([cx-r*0.6,cx+r*0.6],[cy-0.75,cy-0.75],color=BLUE,lw=1.1,zorder=4)
    a.text(cx,cy-1.05,"0",ha="center",va="center",fontsize=12,fontweight="bold",color=NAVY,zorder=4)
    a.text(cx,cy+0.0,"Student\nRecommendation\nPlatform",ha="center",va="center",fontsize=13.5,fontweight="bold",color=NAVY,zorder=4,linespacing=1.2)
    c.entity(1.6,4.3,2.2,2.9,"Student"); c.entity(11.4,4.3,2.2,2.9,"Administrator")
    def edge(y,side):
        dx=math.sqrt(r*r-(y-cy)**2); return (cx-dx if side=="L" else cx+dx, y)
    L,R=2.7,10.3
    for lab,y in [("registration details,\nlogin credentials",3.1),("search request (category,\nlocation, filters)",4.0),("review, report\nof a review",4.9)]:
        p=edge(y,"L"); c.flow([(L,y),p],lab,((L+p[0])/2,y-0.06))
    for lab,y in [("confirmation or\nerror message",3.55),("search results,\nrecommendations",4.45),("review status\nnotification",5.35)]:
        p=edge(y,"L"); c.flow([p,(L,y)],lab,((L+p[0])/2,y-0.06))
    for lab,y in [("admin credentials,\nmanagement data",3.4),("review decision\n(approve / reject)",4.45)]:
        p=edge(y,"R"); c.flow([(R,y),p],lab,((R+p[0])/2,y-0.06))
    for lab,y in [("pending and reported\nreviews",3.95),("student records,\nmanagement confirmation",5.0)]:
        p=edge(y,"R"); c.flow([p,(R,y)],lab,((R+p[0])/2,y-0.06))
    legend0(c); c.save(fn)

def build_level1(fn):
    c=Canvas(18,12.4,"Data Flow Diagram — Level 1","Student Recommendation Platform for New City Students",
             "Practical 8 — Level 1 decomposition of process 0 into processes 1.0 to 4.0 (balanced with the Level 0 flows)")
    a=c.ax
    PL,PR,SM,PW,PH,SW,SH=4.6,13.4,9.0,2.8,1.5,2.6,0.85
    c.entity(1.3,5.2,1.9,1.0,"Student"); c.entity(16.7,5.2,1.9,1.0,"Administrator")
    c.process(PL,2.7,PW,PH,"1.0","Manage Accounts\n(register, verify,\nlogin)")
    c.process(PL,7.4,PW,PH,"2.0","Search and\nRecommend")
    c.process(PR,2.7,PW,PH,"4.0","Administer\nPlatform Data")
    c.process(PR,7.4,PW,PH,"3.0","Manage Reviews")
    c.store(SM,1.9,SW,SH,"D2","Colleges and Cities")
    c.store(SM,3.2,SW,SH,"D1","Users")
    c.store(SM,5.25,SW,SH,"D3","Recommendations")
    c.store(SM,8.0,SW,SH,"D4","Reviews")
    l1,r1,l2,r2=PL-PW/2,PL+PW/2,PR-PW/2,PR+PW/2
    sl,sr=SM-SW/2,SM+SW/2
    c.flow([(0.8,4.7),(0.8,2.3),(l1,2.3)],"registration details,\nlogin credentials",(2.0,2.22))
    c.flow([(l1,3.1),(1.5,3.1),(1.5,4.7)],"confirmation or\nerror message",(2.35,3.18),va="top")
    c.flow([(1.7,5.7),(1.7,7.05),(l1,7.05)],"search request,\nfilters",(2.45,6.98))
    c.flow([(l1,7.75),(1.1,7.75),(1.1,5.7)],"search results,\nrecommendations",(2.15,7.83),va="top")
    c.flow([(0.8,5.7),(0.8,11.0),(PR-0.9,11.0),(PR-0.9,8.15)],"review, report of a review",(6.0,10.95))
    c.flow([(PR+0.9,8.15),(PR+0.9,11.45),(0.5,11.45),(0.5,5.7)],"review status notification",(6.0,11.52),va="top")
    c.flow([(sl,1.95),(r1,2.15)],"college domain",((r1+sl)/2,1.78))
    c.flow([(r1,2.9),(sl,2.95)],"new student\nrecord",((r1+sl)/2,2.88))
    c.flow([(sl,3.45),(r1,3.4)],"account status,\ncredentials",((r1+sl)/2,3.52),va="top")
    c.flow([(sl,5.35),(6.8,5.35),(6.8,6.7),(r1,6.7)],"recommendation\ndata",(6.72,6.0),ha="right",va="center")
    c.flow([(sl,8.0),(r1,7.7)],"published\nreviews",((r1+sl)/2,8.12),va="top")
    c.flow([(l2,7.95),(sr,8.1)],"review records",((l2+sr)/2,8.28),va="top")
    c.flow([(sr,7.75),(l2,7.55)],"pending and\nreported reviews",((l2+sr)/2,7.45))
    c.flow([(l2,6.75),(11.1,6.75),(11.1,5.6),(sr,5.6)],"updated average\nrating",(11.17,6.15),ha="left",va="center")
    c.flow([(l2,2.1),(sr,1.95)],"college and\ncity data",((l2+sr)/2,1.78))
    c.flow([(sr,2.95),(l2,2.9)],"student\nrecords",((l2+sr)/2,2.82))
    c.flow([(l2,3.35),(sr,3.4)],"student status\nupdates",((l2+sr)/2,3.47),va="top")
    c.flow([(PR-0.9,3.45),(PR-0.9,5.0),(sr,5.0)],"recommendation\ndata",(PR-0.97,4.25),ha="right",va="center")
    c.flow([(17.15,4.7),(17.15,2.3),(r2,2.3)],"admin credentials,\nmanagement data",(15.95,2.22))
    c.flow([(r2,3.1),(16.45,3.1),(16.45,4.7)],"student records,\nmanagement\nconfirmation",(15.6,3.18),va="top")
    c.flow([(16.45,5.7),(16.45,6.95),(r2,6.95)],"review decision\n(approve / reject)",(15.6,6.88))
    c.flow([(r2,7.75),(17.15,7.75),(17.15,5.7)],"pending and\nreported reviews",(15.95,7.83),va="top")
    a2=c.ax; W=c.W; ly=9.35
    a2.add_patch(Rectangle((6.1,ly),5.8,1.15,fc="white",ec="#999",lw=1))
    a2.text(6.25,ly+0.2,"Legend",fontsize=10,fontweight="bold",color=NAVY,va="center")
    a2.add_patch(Rectangle((6.25,ly+0.42),0.4,0.22,fc=ENT,ec=ENTE,lw=1.2)); a2.text(6.8,ly+0.53,"External entity",fontsize=9,va="center",color=NAVY)
    a2.add_patch(FancyBboxPatch((8.55,ly+0.42),0.4,0.22,boxstyle="round,pad=0,rounding_size=0.05",fc=FILL,ec=BLUE,lw=1.2)); a2.text(9.05,ly+0.53,"Process",fontsize=9,va="center",color=NAVY)
    a2.add_patch(Rectangle((10.1,ly+0.42),0.4,0.22,fc=STO,ec=STOE,lw=1.2)); a2.text(10.6,ly+0.53,"Data store",fontsize=9,va="center",color=NAVY)
    a2.annotate("",xy=(6.7,ly+0.9),xytext=(6.25,ly+0.9),arrowprops=dict(arrowstyle="-|>",color=NAVY,lw=1.4,mutation_scale=11,shrinkA=0,shrinkB=0))
    a2.text(6.8,ly+0.9,"Data flow",fontsize=9,va="center",color=NAVY)
    c.save(fn)

if __name__=="__main__":
    build_level0("dfd0.png"); build_level1("dfd1.png")
