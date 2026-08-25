CATEGORY_KEYWORDS = {
	"Food": ["swiggy", "zomato", "restaurant", "cafe", "pizza"],
	"Transport": ["uber", "ola", "rapido", "metro", "petrol", "fuel"],
	"Shopping": ["amazon", "flipkart", "myntra", "mall"],
	"Entertainment": ["netflix", "spotify", "cinema", "movie"],
	"Utilities": ["electricity", "water", "gas", "recharge", "broadband"],
	"Healthcare": ["hospital", "pharmacy", "medical", "doctor"],
	"Education": ["udemy", "coursera", "books", "college", "university"],
	"Salary/Income": ["salary", "credited", "payment received"],
	"Transfer": ["neft", "imps", "upi transfer", "sent to"],
}

DEFAULT_CATEGORY = "Other"


def categorize_transaction(description: str) -> str:
	"""
	Assigns a category to a single transaction based on keyword matching.
	Returns the category name, or 'Other' if no keyword matches.
	"""
	if not isinstance(description, str) or description.strip() == "":
		return DEFAULT_CATEGORY

	text = description.lower()

	for category, keywords in CATEGORY_KEYWORDS.items():
		for keyword in keywords:
			if keyword in text:
				return category

	return DEFAULT_CATEGORY


def categorize_dataframe(df):
	"""
	Takes a DataFrame with a 'description' column and adds a 'category' column.
	"""
	df = df.copy()
	df["category"] = df["description"].apply(categorize_transaction)
	return df
