"""Generate a synthetic 5-page XYZ-200 service manual PDF for demos and tests.

Usage: python scripts/make_sample_manual.py
"""
from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parents[2] / "sample_data" / "manuals" / "XYZ-200_Service_Manual.pdf"

PAGES = [
    ("XYZ-200 CNC Machining Center - Service Manual", """
Document revision 3.2. This manual covers installation, operation alarms, troubleshooting and preventive
maintenance for the XYZ-200 CNC machining center.

Safety: Always perform lockout/tagout (LOTO) before opening electrical cabinets or the spindle housing.
Allow the spindle to cool for at least 30 minutes before touching motor surfaces. Wear cut-resistant gloves
when handling tooling. Only qualified maintenance technicians may service the hydraulic unit.

Specifications: Spindle motor 15 kW, max spindle speed 12,000 RPM. Normal spindle motor operating
temperature 40-70 C. Coolant tank capacity 180 litres. Hydraulic system nominal pressure 60 bar."""),
    ("Chapter 2 - Error Codes", """
E001 - Emergency stop active. An E-stop button is pressed or the safety circuit is open. Release all E-stop
buttons and verify the safety relay. If the alarm persists, inspect E-stop contact blocks.

E104 - Spindle motor over-temperature. The spindle motor thermal sensor has exceeded 85 C and the machine
has entered a protective shutdown. Common causes: blocked cooling fan or air filter, low coolant level,
coolant pump failure, clogged radiator fins, or excessive cutting load. See Chapter 3 for the overheating
troubleshooting procedure. Do not reset E104 more than twice without identifying the cause.

E107 - Temperature sensor fault. The spindle thermocouple signal is out of range or erratic. Check the
thermocouple connector for corrosion and verify resistance per the wiring diagram.

E115 - Excessive spindle vibration. Vibration exceeded 7 mm/s RMS. Check tool balance and spindle bearings.

E210 - Hydraulic pressure low. System pressure dropped below 45 bar. See Chapter 4."""),
    ("Chapter 3 - Troubleshooting Overheating", """
Use this procedure when alarm E104 occurs or the spindle motor runs hotter than 70 C.

Step 1: Stop the machine, perform lockout/tagout and allow 30 minutes for cool-down.
Step 2: Inspect the spindle cooling fan intake and air filter. Remove metal dust and replace the filter if
it is more than 50 percent blocked.
Step 3: Check the coolant level in the tank. Refill with approved coolant to the MAX mark if low.
Step 4: Verify coolant pump flow. Rated flow is 25 litres per minute. If flow is more than 20 percent below
rated, inspect the pump impeller and replace it if worn.
Step 5: Inspect the coolant radiator fins and clean them with compressed air from the inside out.
Step 6: Review the cutting program. Reduce feed rate or depth of cut if spindle load exceeds 90 percent.
Step 7: Restart and monitor spindle temperature for one hour. If E104 recurs, contact factory service.

Recurring overheating usually indicates a cooling system issue rather than a motor fault."""),
    ("Chapter 4 - Hydraulic System", """
The hydraulic unit supplies tool clamping and pallet change. Nominal pressure is 60 bar.

Low pressure (alarm E210): check hydraulic fluid level, inspect the pump seal for leaks, and verify the
pressure relief valve setting. Replace the pump seal if fluid is visible around the pump shaft.
Use only ISO VG 32 hydraulic oil. Change the hydraulic filter every 2,000 operating hours."""),
    ("Chapter 5 - Preventive Maintenance Schedule", """
Daily: check coolant level, clean chips from the work area, verify lubrication oil level.
Weekly: clean the spindle cooling fan intake and inspect the air filter.
Monthly: inspect coolant radiator fins, check coolant concentration (5-8 percent), test E-stop buttons.
Every 2,000 hours: replace hydraulic filter, inspect spindle bearings with vibration analysis.
Annually: replace coolant pump impeller, calibrate spindle temperature sensor."""),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for title, body in PAGES:
        page = doc.new_page()
        page.insert_text((72, 80), title, fontsize=16, fontname="helv")
        page.insert_textbox(pymupdf.Rect(72, 110, 540, 780), body.strip(), fontsize=10.5, fontname="helv")
        page.insert_text((72, 810), f"XYZ-200 Service Manual - page {page.number + 1}", fontsize=8, fontname="helv")
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
