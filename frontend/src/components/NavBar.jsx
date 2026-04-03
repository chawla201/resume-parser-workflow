import { NavLink } from 'react-router-dom'
import '../styles/NavBar.css'

export default function NavBar() {
  return (
    <nav className="navbar">
      <span className="navbar-brand">Resume Parser</span>
      <div className="navbar-links">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Upload Resume
        </NavLink>
        <NavLink to="/candidates" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          All Candidates
        </NavLink>
      </div>
    </nav>
  )
}
