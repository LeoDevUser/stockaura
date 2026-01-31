import { useState, useEffect } from 'react'

interface Suggestion {
  ticker: string
  title: string
}

interface SearchBarProps {
  onSelect: (ticker: string) => void;
  placeholder?: string;
}

export default function SearchBar({ onSelect, placeholder = "Search..." }: SearchBarProps) {
  const [input, setInput] = useState<string>('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [_, setLoading] = useState<boolean>(false)

  useEffect(() => {
    if (!input.trim()) {
      setSuggestions([])
      return
    }

    const debounce = setTimeout(async () => {
      setLoading(true)
      try {
        const response = await fetch(`/api/search?q=${input.toUpperCase()}&limit=10`)
        const data: Suggestion[] = await response.json()
        setSuggestions(data)
      } catch (error) {
        console.error('Search failed:', error)
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => clearTimeout(debounce)
  }, [input])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && input.length > 0) {
      onSelect(input.toUpperCase())
      setSuggestions([])
    }
  }

  return (
    <div className="search-box-wrapper">
      <input
        type="text"
        placeholder={placeholder}
        value={input}
        onChange={(e) => setInput(e.target.value)}
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
              onClick={() => {
                onSelect(item.ticker)
                setSuggestions([])
                setInput('')
              }}
            >
              <div className="suggestion-ticker">{item.ticker}</div>
              <div className="suggestion-title">{item.title}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
