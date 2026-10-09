import { useParams } from "react-router-dom";
import { usePoll } from "../api";
import { WindowIcon } from "../components/ui/WindowIcon";
import type { PlanView, RoomNow } from "../types";
import "./Print.css";

/** Today's window timetable on one A4 page: the no-hardware tier. Pin it next to the windows. */
export default function Print() {
  const { roomId = "6B" } = useParams();
  const plan = usePoll<PlanView>(`/v1/rooms/${roomId}/plan`, 60000);
  const room = usePoll<RoomNow>(`/v1/rooms/${roomId}/now`, 60000);
  if (!plan.data || !room.data) return <main className="print"><p>{plan.error ?? "…"}</p></main>;
  const rows = plan.data.timetable;
  return (
    <main className="print">
      <div className="print__actions">
        <button type="button" onClick={() => window.print()}>Print / प्रिंट करें</button>
      </div>
      <header className="print__head">
        <div>
          <p className="print__brand" lang="hi">खिड़की</p>
          <h1><span lang="hi">आज की खिड़की समय-सारणी</span><span>Today's window timetable</span></h1>
        </div>
        <dl>
          <div><dt>Class / कक्षा</dt><dd>{room.data.room_id}</dd></div>
          <div><dt>Date / तारीख़</dt><dd className="num">{plan.data.date}</dd></div>
          <div><dt>Outside / बाहर</dt><dd className="num">AQI {room.data.outdoor.aqi}</dd></div>
        </dl>
      </header>
      <table>
        <thead>
          <tr><th>Time / समय</th><th /><th>Do this / क्या करें</th><th>Why / क्यों</th></tr>
        </thead>
        <tbody>
          {(rows.length === 0 || rows[0].t_min > 450) && <tr>
            <td className="num">07:30</td>
            <td><WindowIcon state="closed" size={28} /></td>
            <td><b lang="hi">खिड़कियाँ बंद रखें</b><span>Start the day with the windows shut</span></td>
            <td><span lang="hi">सुबह बाहर स्मॉग सबसे ज़्यादा होता है।</span><span>Morning smog is usually at its worst.</span></td>
          </tr>}
          {rows.map((r) => (
            <tr key={r.t_min}>
              <td className="num">{r.t}<small>– {r.until}</small></td>
              <td><WindowIcon state={r.window} size={28} /></td>
              <td><b lang="hi">{r.text.hi}</b><span>{r.text.en}</span></td>
              <td><span lang="hi">{r.reason.hi}</span><span>{r.reason.en}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      <footer className="print__foot">
        <p lang="hi">इस पन्ने के लिए किसी सेंसर या टैबलेट की ज़रूरत नहीं। योजना आज के बाहरी हवा के पूर्वानुमान, टाइमटेबल और कक्षा के आकार से बनी है।</p>
        <p>No sensor or tablet needed for this page. Planned from today's outdoor-air forecast (CAMS via Open-Meteo, CC BY 4.0), the timetable and the size of the room. Classroom simulated in this demo. Not a medical device.</p>
      </footer>
    </main>
  );
}
