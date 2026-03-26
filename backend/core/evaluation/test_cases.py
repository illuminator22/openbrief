"""Evaluation test cases for the CA Master Services Agreement (Office Moving Services).

52 test cases across 5 categories for measuring RAG pipeline quality.
Document: 14-1030_Contract_5-14-88-01_Supplier_Application_Terms_and_Conditions.pdf

The document_id is read from config.settings.eval_document_id at runtime.
Expected answers are verified against the actual document content.
"""

from config import settings


def get_test_cases() -> list[dict]:
    """Return all test cases with the configured document ID.

    Returns:
        List of test case dicts, each with: id, category, question,
        document_id, expected_answer, expected_sections.
    """
    doc_id = settings.eval_document_id
    if not doc_id:
        raise RuntimeError(
            "EVAL_DOCUMENT_ID is not configured. Set it in .env to the UUID of "
            "the uploaded CA Master Services Agreement document."
        )

    return [
        # ------------------------------------------------------------------
        # Category 1 — Direct Factual Questions (16 cases)
        # ------------------------------------------------------------------
        {
            "id": "TC001",
            "category": "direct_factual",
            "question": "What is the term of the Master Services Agreement?",
            "document_id": doc_id,
            "expected_answer": "The MSA is effective October 31, 2014 and ends September 30, 2017, with an option to extend for additional one-year periods or a portion thereof. The State reserves the right to terminate for convenience upon thirty days written notice.",
            "expected_sections": ["Section 1"],
        },
        {
            "id": "TC002",
            "category": "direct_factual",
            "question": "When does the Provider Approval Term end?",
            "document_id": doc_id,
            "expected_answer": "The Provider Approval Term is valid until September 30, 2017. Should the MSA be extended, the State may extend the providers list or require providers to re-apply.",
            "expected_sections": ["Section 2"],
        },
        {
            "id": "TC003",
            "category": "direct_factual",
            "question": "Who administers this contract?",
            "document_id": doc_id,
            "expected_answer": "The Department of General Services, Procurement Division (DGS/PD) is the Contract Administrator.",
            "expected_sections": ["Section 5"],
        },
        {
            "id": "TC004",
            "category": "direct_factual",
            "question": "What is the contract number for this MSA?",
            "document_id": doc_id,
            "expected_answer": "The contract number is 5-14-88-01. It appears in the document title.",
            "expected_sections": ["Title/Header"],
        },
        {
            "id": "TC005",
            "category": "direct_factual",
            "question": "Can the State terminate the MSA early?",
            "document_id": doc_id,
            "expected_answer": "Yes, the State reserves the right to terminate the MSA for convenience upon thirty (30) days written notice.",
            "expected_sections": ["Section 1"],
        },
        {
            "id": "TC006",
            "category": "direct_factual",
            "question": "What licenses, permits, and application records must providers have or submit?",
            "document_id": doc_id,
            "expected_answer": "Providers must: be in good standing and authorized to operate in California, submit California business certification or application to Secretary of State, provide a Retailer Seller Permit from the Board of Equalization, hold a CPUC Household Goods Permit for moving services, have a completed Payee Data Record (STD 204) on file, and provide SB/DVBE certification information if applicable.",
            "expected_sections": ["Section 6.1"],
        },
        {
            "id": "TC007",
            "category": "direct_factual",
            "question": "What happens if a provider's license expires during the agreement?",
            "document_id": doc_id,
            "expected_answer": "Providers must deliver a copy of the renewed license or permit within 30 days following the expiration date. If a provider fails to keep required licenses and permits in effect, the State may terminate the agreement.",
            "expected_sections": ["Section 6.1.7"],
        },
        {
            "id": "TC008",
            "category": "direct_factual",
            "question": "How soon must performance start after an order?",
            "document_id": doc_id,
            "expected_answer": "Performance shall start not later than ten calendar days, or on the express date set by the ordering department.",
            "expected_sections": ["Section 10.1"],
        },
        {
            "id": "TC009",
            "category": "direct_factual",
            "question": "What are the grounds for provider suspension?",
            "document_id": doc_id,
            "expected_answer": "Providers may be suspended if they: no longer meet eligibility requirements set forth in Section 6, fail to disclose required information or provide inaccurate or misleading information on the application, fail to promptly notify the State of changes in company information, repeatedly fail to perform or deliver on purchase orders, or receive at least three complaints about products or services within six months.",
            "expected_sections": ["Section 7.1"],
        },
        {
            "id": "TC010",
            "category": "direct_factual",
            "question": "What is the Darfur Contracting Act requirement?",
            "document_id": doc_id,
            "expected_answer": "Public Contract Code Sections 10475-10481 apply to companies that currently or within the previous three years have had business activities outside the United States. Scrutinized companies doing business in Sudan as defined in PCC Section 10476 are ineligible to bid on or submit proposals for state contracts.",
            "expected_sections": ["Section 16"],
        },
        {
            "id": "TC011",
            "category": "direct_factual",
            "question": "What is the minimum protest bond amount?",
            "document_id": doc_id,
            "expected_answer": "The protest bond for the Alternative Protest Process shall not be less than $50,000.00.",
            "expected_sections": ["Section 19"],
        },
        {
            "id": "TC012",
            "category": "direct_factual",
            "question": "How must providers submit a Notice of Intent to Protest?",
            "document_id": doc_id,
            "expected_answer": "A written Notice of Intent to Protest must be received by the Coordinator before close of business 5 p.m. PST/PDT on the 1st working day after issuing the notice of intent. Facsimile is acceptable but email is NOT acceptable.",
            "expected_sections": ["Section 18.1"],
        },
        {
            "id": "TC013",
            "category": "direct_factual",
            "question": "What specific payroll records must providers maintain?",
            "document_id": doc_id,
            "expected_answer": "Providers and subcontractors must keep accurate payroll records showing name, address, social security number, work classification, straight time and overtime hours worked, and actual per diem wages paid. Records must be certified under penalty of perjury stating the information is true and correct and that the employer has complied with Labor Code Section 1720 and Government Code Section 14920.",
            "expected_sections": ["Section 13.2"],
        },
        {
            "id": "TC014",
            "category": "direct_factual",
            "question": "What are the specific penalties for prevailing wage violations?",
            "document_id": doc_id,
            "expected_answer": "Penalties include forfeiture of up to $200 per calendar day or portion thereof for each worker who is underpaid, as determined by the Labor Commissioner based on the nature of the violation. Additionally, the difference between the prevailing wage rates and the amount actually paid to each worker must be paid to the affected workers.",
            "expected_sections": ["Section 13.3"],
        },
        {
            "id": "TC015",
            "category": "direct_factual",
            "question": "Who handles protests for this solicitation?",
            "document_id": doc_id,
            "expected_answer": "The Alternative Protest Process Coordinator at the Department of General Services, Procurement Division, Purchasing Authority Management Section, 707 Third Street, 2nd Floor South, West Sacramento, CA 95605.",
            "expected_sections": ["Section 18.1"],
        },
        {
            "id": "TC016",
            "category": "direct_factual",
            "question": "What is the deadline for filing a complete protest?",
            "document_id": doc_id,
            "expected_answer": "Within seven (7) working days after the last day to submit a Notice of Intent to Protest.",
            "expected_sections": ["Section 18.2"],
        },

        # ------------------------------------------------------------------
        # Category 2 — Section-Specific Questions (10 cases)
        # ------------------------------------------------------------------
        {
            "id": "TC017",
            "category": "section_specific",
            "question": "What does Section 3 say about general provisions?",
            "document_id": doc_id,
            "expected_answer": "Section 3 incorporates General Terms and Conditions (GTC-610), Contractor Certification Clauses (CCC-307), and when commodities are purchased, Non-IT Commodities General Provisions.",
            "expected_sections": ["Section 3"],
        },
        {
            "id": "TC018",
            "category": "section_specific",
            "question": "What is the scope of services under this MSA?",
            "document_id": doc_id,
            "expected_answer": "The MSA solicits applications from qualified moving services companies for office moving services for state and local government. Products and equipment include items needed to support office moves such as boxes, cartons, drums, blankets, wrapping, and crates. Services include move coordination and planning, packing, pickup, unpacking, storage, assembly/disassembly of modular furniture and lab equipment, and furniture delivery and installation.",
            "expected_sections": ["Section 4"],
        },
        {
            "id": "TC019",
            "category": "section_specific",
            "question": "What insurance requirements must providers meet?",
            "document_id": doc_id,
            "expected_answer": "Providers must provide Certificates of Insurance as described in Attachment D.",
            "expected_sections": ["Section 6.2"],
        },
        {
            "id": "TC020",
            "category": "section_specific",
            "question": "What is the suspension procedure?",
            "document_id": doc_id,
            "expected_answer": "Before suspension, the provider receives written notice of the grounds. If grounds for suspension are established, the provider is removed from the approved list. At the end of the suspension period, or when all providers are required to re-apply, the provider may submit a new application.",
            "expected_sections": ["Section 7.2"],
        },
        {
            "id": "TC021",
            "category": "section_specific",
            "question": "What are the prevailing wage requirements?",
            "document_id": doc_id,
            "expected_answer": "Prevailing wage requirements apply to state agency moves. Providers must comply with all applicable provisions of the Labor Code including Section 1720 and Government Code Section 14920. General prevailing wage rate determinations are made by the Department of Industrial Relations. Local government users may also require prevailing wages if listed in their Request for Offer.",
            "expected_sections": ["Section 13"],
        },
        {
            "id": "TC022",
            "category": "section_specific",
            "question": "What is the equipment indemnification clause?",
            "document_id": doc_id,
            "expected_answer": "The Provider shall indemnify the State for any claims against the State relating to loss or damage to the provider's equipment.",
            "expected_sections": ["Section 14"],
        },
        {
            "id": "TC023",
            "category": "section_specific",
            "question": "What does the agreement say about delinquent taxpayers?",
            "document_id": doc_id,
            "expected_answer": "Public Contract Code Section 10295.4 prohibits the State from entering into contracts with delinquent taxpayers.",
            "expected_sections": ["Section 15"],
        },
        {
            "id": "TC024",
            "category": "section_specific",
            "question": "How are applications evaluated?",
            "document_id": doc_id,
            "expected_answer": "Applications are evaluated on the complete Application, and awards are made to responsive and responsible office moving services providers meeting the MSA requirements per the evaluation criteria established herein. Award results in placement on an approved Provider list by county.",
            "expected_sections": ["Section 4.4"],
        },
        {
            "id": "TC025",
            "category": "section_specific",
            "question": "Where can providers get SB/DVBE certification information?",
            "document_id": doc_id,
            "expected_answer": "The Office of Small Business and Disabled Veteran Business Enterprise Certification at the Department of General Services, Procurement Division, 707 Third Street, 1st Floor, Room 400, West Sacramento, CA 95605.",
            "expected_sections": ["Section 6.1.6"],
        },
        {
            "id": "TC026",
            "category": "section_specific",
            "question": "Can the State negotiate with providers?",
            "document_id": doc_id,
            "expected_answer": "Pursuant to Public Contract Code Section 6611, the State may at its sole discretion negotiate with providers. Negotiations may be conducted by any means necessary or appropriate, including email, voice, electronic conferences, or in-person meetings.",
            "expected_sections": ["Section 20"],
        },

        # ------------------------------------------------------------------
        # Category 3 — Inference/Cross-Section Questions (11 cases)
        # ------------------------------------------------------------------
        {
            "id": "TC027",
            "category": "inference",
            "question": "What financial obligations and exposures does a provider face under this agreement?",
            "document_id": doc_id,
            "expected_answer": "Providers face several financial obligations and exposures: prevailing wage penalties of up to $200 per day per underpaid worker plus wage difference payments, equipment indemnification liability for loss or damage claims, insurance costs as described in Attachment D, a $50,000 protest bond requirement, and potential liability for the difference in replacement performance cost if the contractor fails to start work on time.",
            "expected_sections": ["Section 13.3", "Section 14", "Section 6.2", "Section 19"],
        },
        {
            "id": "TC028",
            "category": "inference",
            "question": "What compliance obligations does a provider have?",
            "document_id": doc_id,
            "expected_answer": "Providers must maintain: all required licenses and permits (California business certification, Retailer Seller Permit, CPUC Household Movers License), insurance coverage per Attachment D, prevailing wage compliance with certified payroll records, workers compensation coverage, prompt notification of company information changes, and Darfur Contracting Act certification if applicable.",
            "expected_sections": ["Section 6", "Section 12", "Section 13"],
        },
        {
            "id": "TC029",
            "category": "inference",
            "question": "What happens if a subcontractor doesn't pay prevailing wages?",
            "document_id": doc_id,
            "expected_answer": "The prime contractor is not automatically liable for subcontractor prevailing wage violations unless the prime contractor had knowledge of the failure or did not meet monitoring and corrective requirements. The subcontractor faces penalties including forfeiture of up to $200 per day per underpaid worker plus payment of the wage difference.",
            "expected_sections": ["Section 13.3.3"],
        },
        {
            "id": "TC030",
            "category": "inference",
            "question": "How can a provider lose their approved status?",
            "document_id": doc_id,
            "expected_answer": "Through suspension for cause under Section 7.1 (failure to meet eligibility requirements, inaccurate information, failure to notify of changes, repeated performance failures, or three or more complaints in six months). Also if the MSA expires and the State does not extend the providers list or requires re-application.",
            "expected_sections": ["Section 7", "Section 2"],
        },
        {
            "id": "TC031",
            "category": "inference",
            "question": "What are the time-sensitive obligations in this agreement?",
            "document_id": doc_id,
            "expected_answer": "Key time-sensitive obligations: performance must start within 10 calendar days of an order, license/permit renewal must be delivered within 30 days of expiration, Notice of Intent to Protest must be filed on the 1st working day after notice issuance, complete protest filing within 7 working days of the last day to submit Notice of Intent.",
            "expected_sections": ["Section 10.1", "Section 6.1.7", "Section 18.1", "Section 18.2"],
        },
        {
            "id": "TC032",
            "category": "inference",
            "question": "What external documents are referenced but not included in this agreement?",
            "document_id": doc_id,
            "expected_answer": "Referenced external documents include: General Terms and Conditions (GTC-610), Contractor Certification Clauses (CCC-307), Non-IT Commodities General Provisions, Attachment D (insurance requirements), Attachment E, Attachment F (Office Moving Services Provider Application form), Payee Data Record (STD 204), and Darfur Contracting Act Certification Form.",
            "expected_sections": ["Section 3", "Section 6.2", "Section 21"],
        },
        {
            "id": "TC033",
            "category": "inference",
            "question": "What types of products and services can be purchased under this MSA?",
            "document_id": doc_id,
            "expected_answer": "Products include boxes, cartons, drums, blankets, wrapping, crates, and other items needed to support office moves. Services include move coordination and planning, packing, pickup, unpacking, storage, assembly and disassembly of modular furniture and laboratory equipment, and furniture delivery and installation.",
            "expected_sections": ["Section 4.1.1", "Section 4.1.2"],
        },
        {
            "id": "TC034",
            "category": "inference",
            "question": "What is the relationship between state and local government use of this MSA?",
            "document_id": doc_id,
            "expected_answer": "The MSA is primarily for state agencies. Local government entities may also use it through the Request for Offer (RFO) solicitation process. Prevailing wage requirements apply to state agency moves but local government users may independently require prevailing wages in their RFO. Awards are made by county.",
            "expected_sections": ["Section 4.3", "Section 4.4"],
        },
        {
            "id": "TC035",
            "category": "inference",
            "question": "How long must a provider maintain payroll records?",
            "document_id": doc_id,
            "expected_answer": "Providers must preserve payroll records for a period of three years after completion of work.",
            "expected_sections": ["Section 13.2.5"],
        },
        {
            "id": "TC036",
            "category": "inference",
            "question": "What happens after a provider is suspended?",
            "document_id": doc_id,
            "expected_answer": "The provider is removed from the approved Office Moving Services Provider list. At the end of the suspension period, or whenever all providers are again required to re-apply, the suspended provider may submit a new application for consideration.",
            "expected_sections": ["Section 7.2.2", "Section 7.2.3"],
        },
        {
            "id": "TC037",
            "category": "inference",
            "question": "What are the consequences of submitting inaccurate information on the application?",
            "document_id": doc_id,
            "expected_answer": "Providers who fail to disclose required information or provide inaccurate or misleading information on the Office Moving Services Provider Application form may be suspended and removed from the approved Provider list.",
            "expected_sections": ["Section 7.1.2"],
        },

        # ------------------------------------------------------------------
        # Category 4 — No Answer in Document (10 cases)
        # ------------------------------------------------------------------
        {
            "id": "TC038",
            "category": "no_answer",
            "question": "What are the environmental compliance requirements?",
            "document_id": doc_id,
            "expected_answer": "The document does not contain information about environmental compliance requirements.",
        },
        {
            "id": "TC039",
            "category": "no_answer",
            "question": "Does the agreement include a non-compete clause?",
            "document_id": doc_id,
            "expected_answer": "The document does not contain a non-compete clause.",
        },
        {
            "id": "TC040",
            "category": "no_answer",
            "question": "What is the force majeure clause?",
            "document_id": doc_id,
            "expected_answer": "The document does not include a force majeure clause.",
        },
        {
            "id": "TC041",
            "category": "no_answer",
            "question": "What is the maximum liability cap?",
            "document_id": doc_id,
            "expected_answer": "The document does not specify a liability cap.",
        },
        {
            "id": "TC042",
            "category": "no_answer",
            "question": "What data privacy requirements apply?",
            "document_id": doc_id,
            "expected_answer": "The document does not address data privacy requirements.",
        },
        {
            "id": "TC043",
            "category": "no_answer",
            "question": "What are the intellectual property provisions?",
            "document_id": doc_id,
            "expected_answer": "The document does not contain intellectual property provisions.",
        },
        {
            "id": "TC044",
            "category": "no_answer",
            "question": "What is the arbitration process for general contract disputes after award?",
            "document_id": doc_id,
            "expected_answer": "The document does not specify an arbitration process for general contract disputes after award. It references binding arbitration only for bid protests under the Alternative Protest Process, not for post-award disputes.",
        },
        {
            "id": "TC045",
            "category": "no_answer",
            "question": "What cybersecurity requirements must providers meet?",
            "document_id": doc_id,
            "expected_answer": "The document does not address cybersecurity requirements.",
        },
        {
            "id": "TC046",
            "category": "no_answer",
            "question": "What are the payment terms and invoicing schedule?",
            "document_id": doc_id,
            "expected_answer": "This document does not specify payment terms or invoicing schedules.",
        },
        {
            "id": "TC047",
            "category": "no_answer",
            "question": "Does the agreement require background checks for movers?",
            "document_id": doc_id,
            "expected_answer": "The document does not mention background check requirements for moving personnel.",
        },

        # ------------------------------------------------------------------
        # Category 5 — Edge Cases (5 cases)
        # ------------------------------------------------------------------
        {
            "id": "TC048",
            "category": "edge_case",
            "question": "Tell me about this contract",
            "document_id": doc_id,
            "expected_answer": "This is a Master Services Agreement (Contract 5-14-88-01) for Office Moving Services issued by the State of California Department of General Services. It establishes terms and conditions for providers to be placed on an approved list for office moving services for state and local government agencies.",
        },
        {
            "id": "TC049",
            "category": "edge_case",
            "question": "What is the Retailer Seller Permit?",
            "document_id": doc_id,
            "expected_answer": "All providers furnishing tangible property must provide a copy of their California retailer's seller's permit or permit number issued by the California Board of Equalization (BOE).",
            "expected_sections": ["Section 6.1.3"],
        },
        {
            "id": "TC050",
            "category": "edge_case",
            "question": "CPUC",
            "document_id": doc_id,
            "expected_answer": "The California Public Utilities Commission (CPUC) issues a Household Goods Permit required for providers to perform moving services. Providers must attach a copy of this permit with their application.",
            "expected_sections": ["Section 6.1.4"],
        },
        {
            "id": "TC051",
            "category": "edge_case",
            "question": "What specific dollar amounts are mentioned in the agreement?",
            "document_id": doc_id,
            "expected_answer": "The document mentions several dollar amounts: contracts valued at more than $2,500 require prevailing wages, penalties of up to $200 per calendar day per underpaid worker for prevailing wage violations, and a protest bond of not less than $50,000.00.",
            "expected_sections": ["Section 13", "Section 19"],
        },
        {
            "id": "TC052",
            "category": "edge_case",
            "question": "What are the most minor or routine provisions in this agreement?",
            "document_id": doc_id,
            "expected_answer": "Routine provisions include: information change notification requirements (Section 11), the application completion instructions (Section 21), standard incorporation of General Terms and Conditions (Section 3), and the future application process for unsuccessful proposers (Section 8).",
        },
    ]
