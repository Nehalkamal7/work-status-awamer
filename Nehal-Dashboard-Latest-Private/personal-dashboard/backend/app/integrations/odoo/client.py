import httpx
from app.core.config import get_settings

class OdooError(RuntimeError): pass
class OdooClient:
    def __init__(self):
        s=get_settings(); self.url=s.odoo_url.rstrip("/"); self.db=s.odoo_database; self.username=s.odoo_username; self.password=s.odoo_password; self.uid=None
        self.http=httpx.Client(base_url=self.url,timeout=30,follow_redirects=True)
        self.request_id=0
    def rpc(self,path,params):
        self.request_id+=1
        response=self.http.post(path,json={"jsonrpc":"2.0","method":"call","params":params,"id":self.request_id})
        response.raise_for_status(); payload=response.json()
        if payload.get("error"):
            message=payload["error"].get("data",{}).get("message") or payload["error"].get("message","Odoo API error")
            raise OdooError(message)
        return payload.get("result")
    def authenticate(self):
        if not all([self.url,self.db,self.username,self.password]): raise OdooError("Odoo configuration is incomplete")
        try:
            result=self.rpc("/web/session/authenticate",{"db":self.db,"login":self.username,"password":self.password})
            self.uid=result.get("uid") if result else None
        except (httpx.HTTPError,ValueError) as e: raise OdooError(f"Unable to connect to Odoo: {e}") from e
        if not self.uid: raise OdooError("Invalid Odoo credentials")
        return self.uid
    def execute(self, model, method, args=None, kwargs=None):
        if not self.uid: self.authenticate()
        try: return self.rpc("/web/dataset/call_kw",{"model":model,"method":method,"args":args or [],"kwargs":kwargs or {}})
        except (httpx.HTTPError,ValueError) as e: raise OdooError(f"Odoo API error: {e}") from e
    def projects(self): return self.execute("project.project","search_read",[[]],{"fields":["id","name","partner_id","date_start","date","user_id","active","write_date"],"context":{"active_test":False}})
    def tasks(self): return self.execute("project.task","search_read",[[]],{"fields":["id","name","project_id","user_ids","date_deadline","allocated_hours","effective_hours","progress","priority","stage_id","write_date"],"context":{"active_test":False}})
