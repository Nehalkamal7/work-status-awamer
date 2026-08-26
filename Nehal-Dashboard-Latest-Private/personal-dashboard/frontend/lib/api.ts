const BASE=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000/api";
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
 const token=typeof window!=="undefined"?localStorage.getItem("access_token"):null;
 let response:Response;
 try{response=await fetch(BASE+path,{...options,signal:options.signal||AbortSignal.timeout(15000),headers:{"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`}:{}) ,...options.headers},cache:"no-store"})}
 catch(error){throw new Error(error instanceof DOMException&&error.name==="TimeoutError"?"The backend did not respond. Restart the dashboard and try again.":"Unable to reach the backend.")}
 if(response.status===401&&typeof window!=="undefined"){localStorage.removeItem("access_token");if(location.pathname!=="/login")location.replace("/login");throw new Error("Your session expired. Please sign in again.")}
 if(!response.ok){const payload=await response.json().catch(()=>({detail:"Request failed"}));throw new Error(typeof payload.detail==="string"?payload.detail:"Request failed")}
 return response.status===204?undefined as T:response.json()
}
