import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/LandingPage.css'
import logo from '../assets/logo.png'

interface Suggestion {
  ticker: string
  title: string
}

export default function LandingPage() {
  const [input, setInput] = useState<string>('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [_, setLoading] = useState<boolean>(false)
  const navigate = useNavigate()

  const handleSearch = async (query: string) => {
    setInput(query)
    
    if (query.length === 0) {
      setSuggestions([])
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/search?q=${query.toUpperCase()}&limit=10`)
      const data: Suggestion[] = await response.json()
      setSuggestions(data)
    } catch (error) {
      console.error('Search failed:', error)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelectTicker = (ticker: string) => {
    const title = suggestions.find(s => s.ticker === ticker)?.title
    navigate(`/results?ticker=${ticker}&title=${title}`)
  }

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && input.length > 0) {
      try {
        const response = await fetch(`/api/search?q=${input.toUpperCase()}&limit=1`)
        const data: Suggestion[] = await response.json()
        const title = data.length > 0 ? data[0].title : 'Unknown'
        navigate(`/results?ticker=${input.toUpperCase()}&title=${title}`)
      } catch (error) {
        navigate(`/results?ticker=${input.toUpperCase()}&title=Unknown`)
      }
    }
  }

  return (
    <div className="landing-container">
      <div className="landing-content">
        <div className="logo">
		  <img src={logo} alt="STOCKAURA LOGO"/>
		  {/*<h1>STOCKAURA</h1>*/}
        </div>

        <div className="search-section">
          <div className="search-box-wrapper">
            <input
              type="text"
              placeholder="Enter a stock ticker to analyze it.."
              value={input}
              onChange={(e) => handleSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              className="search-input"
              autoComplete="off"
            />
            
            {suggestions.length > 0 && (
              <div className="suggestions-dropdown">
                {suggestions.map((item) => (
                  <div
                    key={item.ticker}
                    className="suggestion-item"
                    onClick={() => handleSelectTicker(item.ticker)}
                  >
                    <div className="suggestion-ticker">{item.ticker}</div>
                    <div className="suggestion-title">{item.title}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
