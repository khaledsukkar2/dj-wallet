# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial package structure
- `Wallet` model with multi-holder support via GenericForeignKey
- `Transaction` model for deposits and withdrawals
- `Transfer` model for wallet-to-wallet transfers
- `WalletMixin` for easy wallet integration on any model
- `ProductMixin` for purchasable items
- `WalletService` for atomic deposit/withdraw operations
- `TransferService` for safe transfers between wallets
- `ExchangeService` for currency exchange within same holder
- `PurchaseService` for product purchases
- Django signals for balance changes and transaction events
- Django Admin integration
- Comprehensive test structure (unit, integration, security, performance)

## [0.1.0] - 2026-01-14

### Added
- Initial beta release
