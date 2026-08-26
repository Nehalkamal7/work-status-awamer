export type CustomerSatisfaction = { label: string; score: number };

// Google Sheet "Current" and "Support" tabs, reviewed 2026-08-24.
// The sheet is the authoritative source; WhatsApp/Odoo activity must not override it.
export const customerSatisfactionByCode: Record<string, CustomerSatisfaction> = {
  "2091": {label: "راضي جدًا 100%", score: 100},
  "2107": {label: "راضي جدًا 100%", score: 100},
  "AA2110": {label: "راضي جدًا 100%", score: 100},
  "2111": {label: "راضي 80%", score: 80},
  "AA44546": {label: "راضي جدًا 100%", score: 100},
  "AA44819": {label: "راضي جدًا 100%", score: 100},
  "AA41581": {label: "راضي جدًا 100%", score: 100},
  "AA58475": {label: "راضي جدًا 100%", score: 100},
  "AA57068": {label: "راضي جدًا 100%", score: 100},
  "AA58377": {label: "راضي جدًا 100%", score: 100},
  "AA59015": {label: "مقبول 60%", score: 60},
  "AA60523": {label: "راضي جدًا 100%", score: 100},
  "AA47115": {label: "راضي جدًا 100%", score: 100},
  "AA60972": {label: "راضي جدًا 100%", score: 100},
  "AA61569": {label: "راضي جدًا 100%", score: 100},
  "AA62623": {label: "راضي جدًا 100%", score: 100},
  "AA60265": {label: "راضي جدًا 100%", score: 100},
  "AA63106": {label: "راضي جدًا 100%", score: 100},
  "AA59873": {label: "غير راضي 40%", score: 40},
  "AA63801": {label: "راضي جدًا 100%", score: 100},
  "AA62424": {label: "راضي جدًا 100%", score: 100},
  "AA60843": {label: "راضي جدًا 100%", score: 100},
  "AA65712": {label: "راضي جدًا 100%", score: 100},
  "AA51142": {label: "راضي جدًا 100%", score: 100},
  "AA68357": {label: "راضي جدًا 100%", score: 100},
  "AA67663": {label: "راضي جدًا 100%", score: 100},
  "AA64819": {label: "راضي جدًا 100%", score: 100},
  "AA35816": {label: "راضي جدًا 100%", score: 100},
  "2418": {label: "راضي جدًا 100%", score: 100},
  "AA51376": {label: "راضي جدًا 100%", score: 100},
  "AA2429": {label: "راضي 80%", score: 80},
};

export function sheetSatisfaction(code: string): CustomerSatisfaction {
  return customerSatisfactionByCode[code] ?? {
    label: "لا توجد حالة رضا مسجلة في الشيت",
    score: 0,
  };
}
