# ADR 006: ZUGFeRD Profile Selection

## Status

Accepted - 24. Juli 2025

## Context

ZUGFeRD 2.1 offers multiple profiles with varying levels of detail and complexity:

1. **Basic Profile**: Minimal required information for invoicing
2. **Comfort Profile**: Extended information, covering most business cases
3. **Extended Profile**: Comprehensive information for complex business requirements

The eRechnung system needs to determine which profile(s) to support based on business requirements, implementation complexity, and market needs.

## Decision

**We will implement support for the ZUGFeRD 2.1 Comfort Profile only as the initial implementation.**

This decision includes:
- Focus on Comfort Profile implementation for the first release
- Design the system architecture to allow future profile additions
- Implement comprehensive validation for Comfort Profile requirements
- Provide clear documentation for supported features and limitations

## Rationale

The Comfort Profile was selected for the following reasons:

1. **Market Adoption**: The Comfort Profile is the most widely adopted profile in the German market, covering approximately 80-90% of business use cases
2. **Implementation Efficiency**: Focusing on a single profile allows for faster time-to-market and more thorough testing
3. **Complexity Balance**: Comfort Profile provides sufficient detail for most business scenarios without the complexity of the Extended Profile
4. **Future Extensibility**: The system will be designed with a modular approach to easily add Basic or Extended profiles later
5. **Customer Requirements**: Most small to medium businesses require the feature set provided by the Comfort Profile

## Consequences

### Positive Consequences

- **Faster Development**: Single profile focus reduces implementation complexity and development time
- **Better Quality**: More resources can be dedicated to thoroughly implementing and testing one profile
- **Market Coverage**: Comfort Profile addresses the majority of target customer requirements
- **Clear Scope**: Well-defined feature set makes project planning and estimation more accurate
- **Future Growth**: Modular design allows for profile expansion based on market demand

### Negative Consequences

- **Limited Market**: Some customers requiring Basic or Extended profiles may not be immediately served
- **Feature Requests**: Customers may request features from other profiles that are not yet supported
- **Competitive Disadvantage**: Competitors supporting multiple profiles may have broader appeal initially

### Mitigation Strategies

- **Roadmap Communication**: Clearly communicate future profile support plans to customers
- **Modular Architecture**: Design system to easily accommodate additional profiles
- **Market Research**: Continue monitoring customer needs for other profiles
- **Partnership Strategy**: Consider partnerships with solutions that support other profiles

## Implementation Details

### Comfort Profile Features to Implement

1. **Invoice Header Information**
   - Invoice number, date, due date
   - Seller and buyer information
   - Payment terms and methods
   - Currency and tax information

2. **Line Item Details**
   - Product/service descriptions
   - Quantities and units
   - Unit prices and line totals
   - Tax rates and amounts
   - Discount information

3. **Document References**
   - Order references
   - Delivery note references
   - Contract references

4. **Payment Information**
   - Bank account details
   - Payment instructions
   - Early payment discounts

### Future Profile Considerations

- **Basic Profile**: Simplified implementation for basic invoicing needs
- **Extended Profile**: Advanced features for complex business requirements
- **Profile Conversion**: Potential future capability to convert between profiles

## References

- [ZUGFeRD 2.1 Specification](https://www.ferd-net.de/zugferd/specification/index.html)
- [EN16931 Standard](https://ec.europa.eu/digital-building-blocks/wikis/display/DIGITAL/eInvoicing+in+Europe)
- [German Market Analysis for ZUGFeRD Profiles](https://www.ferd-net.de/market-study/)
